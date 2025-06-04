import asyncio
from dataclasses import dataclass, field
from multiprocessing import context
import os
from mcp import Tool
from openai import AsyncOpenAI, NOT_GIVEN
from openai.types import FunctionDefinition
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam
import dotenv
from pydantic import BaseModel
from rich import print as rprint
from rich.markdown import Markdown
from utils import pretty


logger = pretty.ALogger("[ChatOpenAI]")
dotenv.load_dotenv()

DEFAULT_MODEL_NAME = os.environ.get("DEFAULT_MODEL_NAME")

class ToolCallFunction(BaseModel):
    name: str = ""
    arguments: str = ""

class ToolCall(BaseModel):
    id: str
    function: ToolCallFunction = ToolCallFunction()

class ChatOpenAIChatResponse(BaseModel):
    content: str
    tool_calls: list[ToolCall] = []

@dataclass
class AsyncChatOpenAI:
    model: str
    messages: list[ChatCompletionMessageParam] = field(default_factory=list)
    tooles: list[Tool] = field(default_factory=list)

    system_prompt: str = ""
    context: str = ""

    llm: AsyncOpenAI = field(init=False)

    def __post_init__(self) -> None:
        self.llm = AsyncOpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_BASE_URL"),
        )
        if self.system_prompt:
            self.messages.insert(0, {"role": "system", "content": self.system_prompt})
        if self.context:
            self.messages.append(0, {"role": "user", "content": self.context})
    
    async def chat(
        self, prompt: str =  "", print_llm_output: bool = True
        ) -> ChatOpenAIChatResponse:
        try:
            return await self._chat(prompt, print_llm_output)
        except Exception as e:
            rprint(f"[red]ChatOpenAI chat error: {e!s}[/red]")
            raise
    
    async def _chat(
        self, prompt: str =  "", print_llm_output: bool = True
        ) -> ChatOpenAIChatResponse:
        logger.title("Chat")
        if prompt:
            self.messages.append({"role": "user", "content": prompt})
        
        content = ""
        tool_calls: list[ToolCall] = []
        printed_llm_output = False
        async with await self.llm.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=self.get_tools_definitions() or NOT_GIVEN,
            stream=True,
        ) as stream:
            logger.title("LLM Response")
            async for chunk in stream:
                delta = chunk.choices[0].delta
                # 处理content
                if delta.content:
                    content += delta.content or ""
                    if print_llm_output and not printed_llm_output:
                        # print(delta.content, end = "")
                        printed_llm_output = True
                # 处理tool_calls
                if delta.tool_calls:
                    for tool_call in delta.tool_calls:
                        if len(tool_calls) <= tool_call.index:
                            tool_calls.append(ToolCall())
                        this_tool_call = tool_calls[tool_call.index]
                        if tool_call.id:
                            this_tool_call.id += tool_call.id or ""
                        if tool_call.function:
                            if tool_call.function.name:
                                this_tool_call.function.name += (
                                    tool_call.function.name or ""
                                )
                            if tool_call.function.arguments:
                                this_tool_call.function.arguments += (
                                    tool_call.function.arguments or ""
                                )
        if printed_llm_output:
            print()
        self.messages.append(
            {
                "role": "assistant", 
                "content": content,
                "tool_calls":[
                    {
                        "type": "function",
                        "id": tool_call.id,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        },
                    }
                    for tool_call in tool_calls
                ]
            }
        )
        return ChatOpenAIChatResponse(content=content, tool_calls=tool_calls)
    
    def get_tools_definitions(self) -> list[ChatCompletionToolParam]:
        return [
            ChatCompletionToolParam(
                type="function",
                function=FunctionDefinition(
                    name=tool.name,
                    description=tool.description,
                    parameters=tool.inputSchema,
                ),
            )
            for tool in self.tooles
        ]
    
    def append_tool_result(self, tool_call_id: str, tool_result: str) -> None:
        self.messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": tool_result,
            }
        )

async def test():
    print(DEFAULT_MODEL_NAME)
    chat = AsyncChatOpenAI(model=DEFAULT_MODEL_NAME)
    query = input("请输入您的问题：")
    response = await chat.chat(query)
    rprint(Markdown(response.content))
    # rprint(response.tool_calls)
if __name__ == "__main__":
    asyncio.run(test())
        