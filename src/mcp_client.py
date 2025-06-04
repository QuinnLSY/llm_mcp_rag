import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from rich import print as rprint

from dotenv import load_dotenv
from pathlib import Path
from utils.pretty import RICH_CONSOLE

load_dotenv()  # load environment variables from .env
PROJECT_ROOT_DIR = Path(__file__).parent.parent.parent

class MCPClient:
    def __init__(self, name: str, command: str, args: list[str], version: str = "0.0.1") -> None:
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.name = name
        self.command = command
        self.args = args
        self.version = version
        self.tools: list[Tool] = []
    # methods will go here
    async def connect(self) -> None:
        """Connect to an MCP server"""
        await self._connect_to_server()
    
    async def cleanup(self) -> None:
        """Clean up resources"""
        try:
            await self.exit_stack.aclose()
        except Exception:
            rprint("Error during MCP client cleanup, traceback and continue!")
            RICH_CONSOLE.print_exception()
    
    def get_tools(self) -> list[Tool]:
        """Get the list of available tools"""
        return self.tools

    async def call_tools(self, name: str, params:dict[str, Any]):
        return await self.session.call_tool(name, params)

    async def _connect_to_server(self):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        self.tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in self.tools])