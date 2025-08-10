# import resource
import sys
import asyncio
from typing import Optional, Any
from contextlib import AsyncExitStack
from unittest import result
from xmlrpc import client
from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client
import json
from pydantic import AnyUrl


class MCPClient:
    def __init__(
        self,
        server_url: str,
    ):
        self._server_url = server_url
        self._session: Optional[ClientSession] = None
        self._exit_stack: AsyncExitStack = AsyncExitStack()

    async def connect(self):
        streamable_transport = await self._exit_stack.enter_async_context(
            streamablehttp_client(self._server_url)
        )
        _read, _write, _get_session_id = streamable_transport
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(_read, _write)
        )
        await self._session.initialize()

    def session(self) -> ClientSession:
        if self._session is None:
            raise ConnectionError(
                "Client session not initialized or cache not populated. Call connect_to_server first."
            )
        return self._session

    async def list_tools(self) -> list[types.Tool]:
        result_ = await self.session().list_tools()
        return result_.tools

    async def call_tool(
        self, tool_name: str, tool_input: dict
    ) -> types.CallToolResult | None:
        return await self.session().call_tool(tool_name, tool_input)

    async def list_prompts(self) -> list[types.Prompt]:
        result_ = await self.session().list_prompts()
        return result_.prompts

    async def get_prompt(self, prompt_name, args: dict[str, str]):
        result_ = await self.session().get_prompt(prompt_name, args)
        return result_.messages

    async def read_resource(self, uri: str) -> Any:
        result_ = await self.session().read_resource(AnyUrl(uri))
        resource_ = result_.contents[0]

        if isinstance(resource_, types.TextResourceContents):
            if resource_.mimeType == "application/json":
                return json.loads(resource_.text)

            return resource_.text

    async def cleanup(self):
        await self._exit_stack.aclose()
        self._session = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()


# For testing
async def main():
    async with MCPClient(
        server_url="http://localhost:8000/mcp/",
    ) as _client:
        try:
            await _client.connect()
            # Add your test code here
            tools = await _client.list_tools()
            print(f"Available tools: {tools}")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await _client.cleanup()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
