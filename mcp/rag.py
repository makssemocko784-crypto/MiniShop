"""Local semantic retrieval for MiniShop-KB.

Build/rebuild: .venv/Scripts/python.exe -B mcp/rag.py reindex
The explicit build may download the model; searches only use its local cache.
"""

import argparse
import json
import os
from pathlib import Path
import re
import tempfile


NOTES_DIR = Path(r"C:\MiniShop-KB")
INDEX_DIR = Path(__file__).resolve().parents[1] / "evaluation" / "vector_index"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
INDEX_VERSION = 1


def note_files(notes_dir):
    """Prune excluded directories before visiting their files."""
    notes_dir = Path(notes_dir)
    if not notes_dir.is_dir():
        raise FileNotFoundError(f"База знань недоступна: {notes_dir}")
    paths = []
    for directory, subdirs, filenames in os.walk(notes_dir, followlinks=False):
        subdirs[:] = sorted(
            name for name in subdirs
            if name.casefold() not in {".git", ".obsidian"}
            and not (Path(directory) / name).is_symlink()
        )
        for name in filenames:
            path = Path(directory) / name
            if path.suffix.casefold() == ".md" and not path.is_symlink():
                paths.append(path)
    return sorted(paths)


def manifest(paths, notes_dir):
    result = []
    for path in paths:
        stat = path.stat()
        result.append([path.relative_to(notes_dir).as_posix(), stat.st_size, stat.st_mtime_ns])
    return result


def sections(text):
    """Split on ATX headings, keeping fenced code inside its section."""
    heading, lines, fence = "", [], None
    for line in text.splitlines():
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line) if fence is None else None
        if match:
            content = "\n".join(lines).strip()
            if content:
                yield heading, content
            heading, lines = match.group(1), [line]
        else:
            lines.append(line)
    content = "\n".join(lines).strip()
    if content:
        yield heading, content


class VectorIndex:
    def __init__(self, notes_dir=NOTES_DIR, index_dir=INDEX_DIR):
        self.notes_dir = Path(notes_dir).resolve()
        self.index_dir = Path(index_dir).resolve()
        self.index_path = self.index_dir / "index.npz"
        self._model = None

    def model(self, allow_download=False):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as error:
                raise RuntimeError(
                    "Встановіть залежності: .venv/Scripts/python.exe -m pip install "
                    "sentence-transformers numpy"
                ) from error
            self._model = SentenceTransformer(
                MODEL_NAME,
                cache_folder=str(self.index_dir / "model_cache"),
                local_files_only=not allow_download,
                device="cpu",
            )
        return self._model

    @staticmethod
    def numpy():
        try:
            import numpy as np
        except ImportError as error:
            raise RuntimeError(
                "Встановіть залежності: .venv/Scripts/python.exe -m pip install "
                "sentence-transformers numpy"
            ) from error
        return np

    def chunks(self, paths, model):
        chunks = []
        tokenizer = model.tokenizer
        budget = model.max_seq_length - tokenizer.num_special_tokens_to_add(pair=False)
        if budget < 1:
            raise ValueError("Некоректна максимальна довжина моделі.")
        for path in paths:
            for heading, content in sections(path.read_text(encoding="utf-8-sig")):
                tokens = tokenizer.encode(content, add_special_tokens=False)
                # Split oversized sections too, so the model does not truncate them.
                fragments = [content] if len(tokens) <= budget else [
                    tokenizer.decode(tokens[start:start + budget], skip_special_tokens=True)
                    for start in range(0, len(tokens), budget)
                ]
                for fragment in fragments:
                    chunks.append({
                        "name": path.stem,
                        "path": path.relative_to(self.notes_dir).as_posix(),
                        "heading": heading,
                        "content": fragment,
                    })
        return chunks

    def reindex(self, allow_download=True):
        np = self.numpy()
        paths = note_files(self.notes_dir)
        before = manifest(paths, self.notes_dir)
        model = self.model(allow_download=allow_download) if paths else None
        chunks = self.chunks(paths, model) if paths else []
        vectors = np.asarray(model.encode(
            [chunk["content"] for chunk in chunks],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        ), dtype=np.float32) if chunks else np.empty((0, 0), dtype=np.float32)
        if before != manifest(note_files(self.notes_dir), self.notes_dir):
            raise RuntimeError("Нотатки змінилися під час індексації; повторіть reindex.")
        metadata = {
            "version": INDEX_VERSION,
            "model": MODEL_NAME,
            "notes_dir": str(self.notes_dir),
            "manifest": before,
            "chunks": chunks,
        }
        self.index_dir.mkdir(parents=True, exist_ok=True)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(dir=self.index_dir, suffix=".npz", delete=False) as stream:
                temporary_path = Path(stream.name)
                np.savez_compressed(
                    stream, vectors=vectors,
                    metadata=np.array(json.dumps(metadata, ensure_ascii=False)),
                )
            os.replace(temporary_path, self.index_path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        return len(chunks)

    def search(self, query, top_k=5):
        if not query.strip() or top_k <= 0:
            return []
        if not self.index_path.is_file():
            raise RuntimeError("Індекс відсутній. Виконайте: .venv/Scripts/python.exe -B mcp/rag.py reindex")
        np = self.numpy()
        with np.load(self.index_path, allow_pickle=False) as data:
            metadata = json.loads(str(data["metadata"].item()))
            vectors = data["vectors"]
        if (
            metadata.get("version") != INDEX_VERSION
            or metadata.get("model") != MODEL_NAME
            or metadata.get("notes_dir") != str(self.notes_dir)
            or metadata.get("manifest") != manifest(note_files(self.notes_dir), self.notes_dir)
        ):
            raise RuntimeError("Індекс застарів. Виконайте: .venv/Scripts/python.exe -B mcp/rag.py reindex")
        chunks = metadata["chunks"]
        if vectors.ndim != 2 or vectors.shape[0] != len(chunks) or not np.isfinite(vectors).all():
            raise ValueError("Пошкоджений індекс; повторіть reindex.")
        if not chunks:
            return []
        query_vector = self.model().encode(
            [query], normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False,
        )[0]
        scores = vectors @ query_vector
        order = np.argsort(-scores, kind="stable")[:top_k]
        return [
            {**chunks[int(index)], "score": f"{float(scores[index]):.6f}"}
            for index in order if scores[index] > 0
        ]


_index = VectorIndex()


def search_notes(query: str) -> list[dict[str, str]]:
    """Return up to five closest fragments, with file paths and cosine scores."""
    return _index.search(query)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["reindex"])
    parser.add_argument("--offline", action="store_true", help="Use only the cached model")
    args = parser.parse_args()
    print(f"Indexed chunks: {_index.reindex(allow_download=not args.offline)}")


if __name__ == "__main__":
    main()
