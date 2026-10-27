"""Offline checks; vector checks require NumPy but never download a model."""

import importlib.util
from pathlib import Path
import tempfile
import unittest


spec = importlib.util.spec_from_file_location(
    "minishop_rag", Path(__file__).resolve().parents[1] / "mcp" / "rag.py"
)
rag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rag)


class Tokenizer:
    def num_special_tokens_to_add(self, pair=False):
        return 2

    def encode(self, text, add_special_tokens=False):
        return text.split()

    def decode(self, tokens, skip_special_tokens=True):
        return " ".join(tokens)


class FakeModel:
    tokenizer = Tokenizer()
    max_seq_length = 10

    def encode(self, texts, **kwargs):
        import numpy as np

        vectors = np.array([
            [float("JSON" in text), float("Guardrails" in text)] for text in texts
        ], dtype=np.float32)
        lengths = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / np.where(lengths == 0, 1, lengths)


class RagTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.notes = self.root / "notes"
        self.notes.mkdir()
        self.index = rag.VectorIndex(self.notes, self.root / "index")
        self.index._model = FakeModel()

    def test_excluded_directories_and_markdown_suffix(self):
        for directory in (".git", ".obsidian", "Decisions/.Obsidian", "Decisions"):
            target = self.notes / directory
            target.mkdir(parents=True, exist_ok=True)
            (target / "note.MD").write_text("JSON", encoding="utf-8")
        (self.notes / "other.txt").write_text("JSON", encoding="utf-8")
        self.assertEqual(
            [path.relative_to(self.notes).as_posix() for path in rag.note_files(self.notes)],
            ["Decisions/note.MD"],
        )

    def test_headings_and_fenced_code(self):
        text = "Intro\n# One\ntext\n```python\n# code\n```\n## Two\nmore"
        parts = list(rag.sections(text))
        self.assertEqual([heading for heading, _ in parts], ["", "One", "Two"])
        self.assertIn("# code", parts[1][1])

    def test_long_sections_fit_model_budget_and_preserve_words(self):
        path = self.notes / "long.md"
        content = " ".join(f"word{i}" for i in range(25))
        path.write_text(content, encoding="utf-8")
        chunks = self.index.chunks([path], FakeModel())
        self.assertTrue(all(len(chunk["content"].split()) <= 8 for chunk in chunks))
        self.assertEqual(" ".join(chunk["content"] for chunk in chunks), content)

    def test_empty_query_and_missing_index(self):
        self.assertEqual(self.index.search("   "), [])
        with self.assertRaisesRegex(RuntimeError, "reindex"):
            self.index.search("JSON")

    def test_missing_vault_is_an_error(self):
        with self.assertRaises(FileNotFoundError):
            rag.note_files(self.root / "missing")

    @unittest.skipUnless(importlib.util.find_spec("numpy"), "NumPy is not installed")
    def test_vector_ranking_persistence_and_stale_index(self):
        (self.notes / "storage.md").write_text("# Storage\nJSON", encoding="utf-8")
        (self.notes / "safety.md").write_text("# Safety\nGuardrails", encoding="utf-8")
        self.assertEqual(self.index.reindex(), 2)
        reloaded = rag.VectorIndex(self.notes, self.index.index_dir)
        reloaded._model = FakeModel()
        result = reloaded.search("JSON")
        self.assertEqual(result[0]["path"], "storage.md")
        self.assertIn("JSON", result[0]["content"])
        self.assertAlmostEqual(float(result[0]["score"]), 1.0)
        (self.notes / "storage.md").write_text("# Storage\nJSON changed", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "reindex"):
            reloaded.search("JSON")
        reloaded.reindex()
        self.assertIn("changed", reloaded.search("JSON")[0]["content"])
        (self.notes / "storage.md").unlink()
        with self.assertRaisesRegex(RuntimeError, "reindex"):
            reloaded.search("JSON")

    @unittest.skipUnless(importlib.util.find_spec("numpy"), "NumPy is not installed")
    def test_empty_index(self):
        self.assertEqual(self.index.reindex(), 0)
        self.assertEqual(self.index.search("JSON"), [])


if __name__ == "__main__":
    unittest.main()
