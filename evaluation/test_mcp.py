import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    params = StdioServerParameters(
        command=sys.executable,
        args=[r"C:\MiniShop\mcp\server.py"],
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await asyncio.wait_for(session.initialize(), timeout=180)
            print("MCP connected", flush=True)

            result = await asyncio.wait_for(
                session.call_tool(
                    "search_notes",
                    {"query": "Як у MiniShop зберігаються дані?"},
                ),
                timeout=180,
            )
            print(result)

asyncio.run(main())