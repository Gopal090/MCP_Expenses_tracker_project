import asyncio
import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import ToolMessage

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

SERVERS = {
    "expense": {
        "transport": "streamable_http",
        "url": os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")
    }
}

async def main():
    print(f"Connecting to remote MCP server at {SERVERS['expense']['url']}...")
    client = MultiServerMCPClient(SERVERS)
    tools = await client.get_tools()

    named_tools = {tool.name: tool for tool in tools}
    print("Available tools on MCP Server:", list(named_tools.keys()))

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("\nNote: Set GROQ_API_KEY in .env to run the full LLM prompt test.")
        return

    llm = ChatGroq(model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"), groq_api_key=api_key)
    llm_with_tools = llm.bind_tools(tools)

    prompt = "Add an expense of 120 dollars for Groceries on 2026-11-17 with note 'Weekly shopping'."
    print(f"\nUser Prompt: {prompt}")
    response = await llm_with_tools.ainvoke(prompt)

    if not getattr(response, "tool_calls", None):
        print("\nLLM Reply:", response.content)
        return

    tool_messages = []
    for tc in response.tool_calls:
        selected_tool = tc["name"]
        selected_tool_args = tc.get("args") or {}
        selected_tool_id = tc["id"]
        print(f"Executing Tool [{selected_tool}] with args: {selected_tool_args}")

        result = await named_tools[selected_tool].ainvoke(selected_tool_args)
        print("Tool Result:", result)
        tool_messages.append(ToolMessage(tool_call_id=selected_tool_id, content=json.dumps(result)))

    final_response = await llm_with_tools.ainvoke([prompt, response, *tool_messages])
    print(f"\nFinal LLM Response:\n{final_response.content}")

if __name__ == '__main__':
    asyncio.run(main())
