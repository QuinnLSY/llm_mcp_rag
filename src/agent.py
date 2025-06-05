
from dataclasses import dataclass
import asyncio
from pathlib import Path
import os
import dotenv
import json
from chat_openai import AsyncChatOpenAI
from mcp_client import MCPClient
from mcp_tool import PresetMcpTools
from utils import pretty
from utils.pretty import RICH_CONSOLE as console
from rich import print as rprint

dotenv.load_dotenv()  # load environment variables from.env

logger = pretty.ALogger("[Agent]")
DEFAULT_MODEL_NAME = os.environ.get("DEFAULT_MODEL_NAME")
PROJECT_ROOT_DIR = Path(__file__).parent.parent

@dataclass
class Agent:
    mcp_clients: list[MCPClient]
    llm: AsyncChatOpenAI | None = None
    model: str = ""
    systenPrompt: str = ""
    context: str = ""

    async def create(self) -> None:
        logger.title("INIT LLM and TOOLS")
        tools = []
        for mcp_client in self.mcp_clients:
            await mcp_client.connect()
            tools.extend(mcp_client.get_tools())

        self.llm = AsyncChatOpenAI(
            model=self.model,
            tools=tools,
            system_prompt=self.systenPrompt,
            context=self.context
        )
    
    async def cleanup(self) -> None:
        logger.title("CLEANUP LLM and TOOLS")
        while self.mcp_clients:
            mcp_client = self.mcp_clients.pop()
            await mcp_client.cleanup()
    
    async def invoke(self, prompt: str) -> str | None:
        return await self._invoke(prompt)
    
    async def _invoke(self, prompt: str) -> str | None:
        if not self.llm:
            raise ValueError("[red]LLM not initialized[/red]")
        
        response = await self.llm.chat(prompt)
        i = 0
        while True:
            i += 1
            logger.title(f"AGENT INVOKE {i}")
            # rprint(response)
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    target_mcp_client:  MCPClient | None = None
                    for mcp_client in self.mcp_clients:
                        if tool_call.function.name in [
                            tool.name for tool in mcp_client.get_tools()
                        ]:
                            target_mcp_client = mcp_client
                            break

                    if target_mcp_client:
                        logger.title(f"Calling tool {tool_call.function.name}")
                        console.log(f"[green]Calling tool {tool_call.function.name}[/green]")
                        console.log(f"[green]Tool args: {tool_call.function.arguments}[/green]")
                        tool_result = await target_mcp_client.call_tool(tool_call.function.name, json.loads(tool_call.function.arguments))
                        console.log(f"[green]Tool result: {tool_result}[/green]")
                        self.llm.append_tool_result(tool_call.id, tool_result.model_dump_json())
                    else:
                        console.log(f"[red]Tool {tool_call.function.name} not found[/red]")
                        self.llm.append_tool_result(tool_call.id, "Tool not found")
                response = await self.llm.chat()
            
            else:
                return response.content        

async def test():
    mcp_clients = []
    agent = None
    try:
        for mcp_tool in [
        PresetMcpTools.filesystem.append_mcp_params(f"{PROJECT_ROOT_DIR!s}"),
        PresetMcpTools.fetch
    ]:
            rprint(mcp_tool.shell_cmd)
            mcp_client = MCPClient(**mcp_tool.to_common_params())
            mcp_clients.append(mcp_client)
        
        agent = Agent(
            mcp_clients=mcp_clients,
            model=DEFAULT_MODEL_NAME,
        )
        await agent.create()

        # query = input("请输入您的问题：")

        res = await agent.invoke(f"读取 https://leetcode.cn/problems/two-sum/description/ 的题目, 并将解题代码保存在 {PROJECT_ROOT_DIR} 目录下的code.md文件中")
        rprint(res)
    except Exception as e:
            rprint(f"[red]ERROR DURING AGENT EXCUTION:{e!s}[/red]")
            raise
    finally:
        if agent:
            await agent.cleanup()
if __name__ == "__main__":
    asyncio.run(test())



    