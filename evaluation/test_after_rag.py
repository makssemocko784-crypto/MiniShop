"""Compare ten queries using the existing index, with model downloads disabled."""

import importlib.util
import json
import os
from pathlib import Path
import sys


EVALUATION_DIR = Path(__file__).resolve().parent


def load_search_notes():
    # Set before importing any Hugging Face libraries; cached model files only.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    source_path = EVALUATION_DIR.parent / "mcp" / "rag.py"
    spec = importlib.util.spec_from_file_location("minishop_evaluation_rag", source_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not (module.INDEX_DIR / "index.npz").is_file():
        raise FileNotFoundError("Побудований індекс відсутній; автоматична індексація заборонена.")
    return module.search_notes


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    queries = [
        line.strip()
        for line in (EVALUATION_DIR / "queries.txt").read_text(
            encoding="utf-8-sig"
        ).splitlines()
        if line.strip()
    ]
    if len(queries) != 10:
        raise ValueError(f"Очікується 10 запитів, отримано: {len(queries)}.")
    before = json.loads((EVALUATION_DIR / "before_rag.json").read_text(encoding="utf-8-sig"))
    if [record["query"] for record in before] != queries:
        raise ValueError("Запити before_rag.json не збігаються з queries.txt.")
    if not all(isinstance(record["results"], list) for record in before):
        raise ValueError("Некоректні результати у before_rag.json.")

    search_notes = load_search_notes()
    records = [
        {"query": query, "results": search_notes(query)}
        for query in queries
    ]
    output_path = EVALUATION_DIR / "after_rag.json"
    output_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    after = json.loads(output_path.read_text(encoding="utf-8"))

    print(f"{'Запит':55} | {'До':>3} | {'Після':>5} | Найрелевантніша нотатка")
    print("-" * 105)
    for old, new in zip(before, after):
        query = new["query"]
        label = query if len(query) <= 55 else query[:52] + "..."
        results = new["results"]
        best_note = results[0]["path"] if results else "—"
        print(f"{label:55} | {len(old['results']):>3} | {len(results):>5} | {best_note}")
    print(f"Збережено: {output_path}")
    print("Після RAG пораховано фрагменти; кількість сама по собі не оцінює релевантність.")


if __name__ == "__main__":
    main()
