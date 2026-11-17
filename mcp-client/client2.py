# client2.py — Minimal MCP + Streamlit chat with Remote FastMCP Server

import os
import json
import asyncio
import streamlit as st
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Backend credentials (hidden from UI)
api_key = os.getenv("GROQ_API_KEY", "")
model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
server_url = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")

SERVERS = {
    "expense": {
        "transport": "streamable_http",
        "url": server_url
    }
}

SYSTEM_PROMPT = (
    "You are a helpful expense tracking assistant. You have access to tools to add, list, and summarize expenses. "
    "When you choose to call a tool, do not narrate status updates. "
    "After tools run, return a clear, helpful final answer."
)

st.set_page_config(page_title="MCP Chat", page_icon="🧰", layout="centered")
st.title("🧰 Expense Tracker MCP Chat")

# One-time init
if "initialized" not in st.session_state:
    try:
        st.session_state.client = MultiServerMCPClient(SERVERS)
        tools = asyncio.run(st.session_state.client.get_tools())
        st.session_state.tools = tools
        st.session_state.tool_by_name = {t.name: t for t in tools}
        st.session_state.server_ok = True
    except Exception as e:
        st.session_state.server_ok = False
        st.session_state.server_err = str(e)
        st.session_state.tools = []
        st.session_state.tool_by_name = {}

    st.session_state.history = [SystemMessage(content=SYSTEM_PROMPT)]
    st.session_state.initialized = True

if not st.session_state.get("server_ok", False):
    st.error(f"Failed to connect to MCP Server at {server_url}: {st.session_state.get('server_err')}")

# Render chat history
for msg in st.session_state.history:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.markdown(msg.content)
    elif isinstance(msg, AIMessage):
        if getattr(msg, "tool_calls", None):
            continue
        with st.chat_message("assistant"):
            st.markdown(msg.content)

# Chat input
user_text = st.chat_input("Type a message…")
if user_text:
    if not api_key:
        st.error("GROQ_API_KEY is not configured in .env.")
        st.stop()

    with st.chat_message("user"):
        st.markdown(user_text)
    st.session_state.history.append(HumanMessage(content=user_text))

    llm = ChatGroq(model=model_name, groq_api_key=api_key, temperature=0)
    llm_with_tools = llm.bind_tools(st.session_state.tools)

    # First pass: let the model decide whether to call tools
    first = asyncio.run(llm_with_tools.ainvoke(st.session_state.history))
    tool_calls = getattr(first, "tool_calls", None)

    if not tool_calls:
        with st.chat_message("assistant"):
            st.markdown(first.content or "")
        st.session_state.history.append(first)
    else:
        st.session_state.history.append(first)

        tool_msgs = []
        for tc in tool_calls:
            name = tc["name"]
            args = tc.get("args") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    pass
            tool = st.session_state.tool_by_name[name]
            res = asyncio.run(tool.ainvoke(args))
            tool_msgs.append(ToolMessage(tool_call_id=tc["id"], content=json.dumps(res)))

        st.session_state.history.extend(tool_msgs)

        # Final assistant reply
        final = asyncio.run(llm.ainvoke(st.session_state.history))
        with st.chat_message("assistant"):
            st.markdown(final.content or "")
        st.session_state.history.append(AIMessage(content=final.content or ""))
