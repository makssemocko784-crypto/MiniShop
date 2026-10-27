"""Run the saved pre-RAG search against the ten evaluation queries."""

import ast
import json
import sys
from pathlib import Path


EVALUATION_DIR = Path(__file__).resolve().parent


def load_search_notes():
    """Load only the original function, without MCP imports or decorators."""
    source_path = EVALUATION_DIR / "server_before_rag.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8-sig"), str(source_path))
    functions = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "search_notes"
    ]
    if len(functions) != 1:
        raise ValueError("Очікується одна функція search_notes у server_before_rag.py.")
    function = functions[0]
    function.decorator_list = []
    module = ast.Module(body=[function], type_ignores=[])
    namespace = {"Path": Path}
    exec(compile(ast.fix_missing_locations(module), str(source_path), "exec"), namespace)
    return namespace["search_notes"]


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
    if not Path(r"C:\MiniShop-KB").is_dir():
        raise FileNotFoundError("База знань C:\\MiniShop-KB недоступна.")

    search_notes = load_search_notes()
    records = [
        {"query": query, "results": search_notes(query)}
        for query in queries
    ]
    output_path = EVALUATION_DIR / "before_rag.json"
    output_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"{'№':>2} | {'Запит':60} | {'Знайдено':>8}")
    print("-" * 78)
    for number, record in enumerate(records, start=1):
        query = record["query"]
        label = query if len(query) <= 60 else query[:57] + "..."
        print(f"{number:>2} | {label:60} | {len(record['results']):>8}")
    print(f"Збережено: {output_path}")


if __name__ == "__main__":
    main()
