from pathlib import Path
import re
import subprocess
import asyncio
from rag import search_notes as semantic_search_notes

try:
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError:
    from mcp.server.mcpserver import MCPServer as FastMCP


mcp = FastMCP("minishop-kb")


@mcp.tool()
def ping() -> str:
    return "MiniShop MCP OK"


@mcp.tool()
def search_notes(query: str) -> list[dict[str, str]]:
    """Semantic search returning name, path, content and cosine score for each fragment."""
    return semantic_search_notes(query)


@mcp.tool()
async def ingest_note(name: str, content: str) -> str:
    if (
        not name
        or name != name.strip()
        or name.endswith(".")
        or re.search(r'[<>:"/\\|?*\x00-\x1f\x7f]', name)
        or name in {".", ".."}
        or name.split(".", 1)[0].upper()
        in {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
        or re.fullmatch(r"(?:COM|LPT)[1-9¹²³]", name.split(".", 1)[0], re.I)
        or len((name + ".md").encode("utf-16-le")) > 510
    ):
        raise ValueError("Unsafe note name")

    repo_dir = Path(r"C:\MiniShop-KB").resolve()
    decisions_dir = repo_dir / "Decisions"
    if decisions_dir.resolve() != decisions_dir:
        raise ValueError("Decisions must not redirect to another directory")
    note_path = decisions_dir / (name + ".md")
    if note_path.is_symlink() or note_path.resolve().parent != decisions_dir:
        raise ValueError("Note must remain inside Decisions")

    data = content.encode("utf-8")
    exists = note_path.exists()
    if exists and note_path.read_bytes() == data:
        return "unchanged"

    decisions_dir.mkdir(parents=True, exist_ok=True)
    note_path.write_bytes(data)
    return "updated" if exists else "created"


if __name__ == "__main__":
    # Initialize native NumPy/Torch libraries before MCP starts stdio reader threads.
    # Importing them for the first time inside a request can deadlock on Windows.
    import sentence_transformers

    mcp.run(transport="stdio")
