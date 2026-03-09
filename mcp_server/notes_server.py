import asyncio
import sys
from pathlib import Path

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.tools.notes_tool import list_notes, save_note, search_notes

# Create MCP server instance
server = Server("productivity-notes")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Declare the tools this MCP server exposes."""
    return [
        types.Tool(
            name="save_note",
            description="Save a note with a title and content to persistent storage.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title of the note"},
                    "content": {
                        "type": "string",
                        "description": "Full content of the note",
                    },
                    "tags": {
                        "type": "string",
                        "description": "Comma-separated tags, optional",
                    },
                },
                "required": ["title", "content"],
            },
        ),
        types.Tool(
            name="list_notes",
            description="List recently saved notes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max notes to return (default 10)",
                        "default": 10,
                    }
                },
            },
        ),
        types.Tool(
            name="search_notes",
            description="Search notes by keyword in title or content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Keyword to search for",
                    }
                },
                "required": ["keyword"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle incoming tool calls from any MCP client."""
    try:
        if name == "save_note":
            result = save_note(
                title=arguments["title"],
                content=arguments["content"],
                tags=arguments.get("tags", ""),
            )
        elif name == "list_notes":
            result = list_notes(limit=arguments.get("limit", 10))
        elif name == "search_notes":
            result = search_notes(keyword=arguments["keyword"])
        else:
            result = {"error": f"Unknown tool: {name}"}

        import json

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
