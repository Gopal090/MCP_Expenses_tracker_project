import os
import json
import asyncio
import tempfile
import sqlite3
import streamlit as st
from datetime import date
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

# Load environment variables (from local and parent directories)
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Internal credentials & configuration (hidden from UI)
api_key = os.getenv("GROQ_API_KEY", "")
model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
server_url = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")

# Streamlit page setup
st.set_page_config(
    page_title="Expense Tracker - MCP Chatbot",
    page_icon="💰",
    layout="wide"
)

# Custom styling for badges and containers
st.markdown("""
<style>
    .reportview-container {
        margin-top: -2em;
    }
    .stChatFloatingInputContainer {
        bottom: 20px;
    }
    .tool-box {
        background-color: #f0f2f6;
        border-radius: 8px;
        padding: 10px;
        margin: 5px 0px;
        font-family: monospace;
        font-size: 0.85em;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# Sidebar: Server Status & Data Management
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ MCP Server Status")
    
    # Connect to Remote MCP Server
    SERVERS = {
        "expense_server": {
            "transport": "streamable_http",
            "url": server_url
        }
    }

    async def fetch_tools(server_config):
        client = MultiServerMCPClient(server_config)
        tools = await client.get_tools()
        return client, tools

    # Initialize or reinitialize MCP client
    if "mcp_tools" not in st.session_state or st.session_state.get("current_server_url") != server_url:
        try:
            with st.spinner("Connecting to remote MCP server..."):
                client, tools = asyncio.run(fetch_tools(SERVERS))
                st.session_state.mcp_client = client
                st.session_state.mcp_tools = tools
                st.session_state.tool_by_name = {t.name: t for t in tools}
                st.session_state.current_server_url = server_url
                st.session_state.server_connected = True
        except Exception as e:
            st.session_state.server_connected = False
            st.session_state.server_error = str(e)
            st.session_state.mcp_tools = []
            st.session_state.tool_by_name = {}

    if st.session_state.get("server_connected", False):
        st.success("🟢 FastMCP Server Connected")
        with st.expander("🛠️ Available MCP Tools", expanded=True):
            for t in st.session_state.mcp_tools:
                st.markdown(f"**`{t.name}`**")
                st.caption(t.description or "No description provided.")
    else:
        st.error("🔴 MCP Server Offline")
        st.warning(f"Could not reach {server_url}. Make sure test-remote-mcp-server is running.")
        if "server_error" in st.session_state:
            with st.expander("Error details"):
                st.code(st.session_state.server_error)

    st.divider()
    st.subheader("🧹 Actions")
    
    # Clear Chat History
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.history = []
        st.session_state.tool_traces = {}
        st.rerun()

    # Reset Database
    if st.button("⚠️ Reset Database (Delete All)", use_container_width=True):
        db_path = os.path.join(tempfile.gettempdir(), "expenses.db")
        try:
            if os.path.exists(db_path):
                with sqlite3.connect(db_path) as c:
                    c.execute("DELETE FROM expenses")
                    c.commit()
            st.session_state.history = []
            st.session_state.tool_traces = {}
            st.success("Database has been completely reset!")
            st.rerun()
        except Exception as e:
            st.error(f"Error resetting database: {e}")

# ─────────────────────────────────────────────────────────────
# Main Chat Header (Clean, no API key or model displayed)
# ─────────────────────────────────────────────────────────────
st.title("💰 Expense Tracker MCP Chatbot")
st.caption("Powered by **FastMCP** (Server) + **LangChain MCP Adapters** (Client)")

today_str = date.today().isoformat()
SYSTEM_PROMPT = f"""You are a helpful personal finance assistant with direct access to an Expense Tracker database via MCP tools.
Today's date is {today_str}.

Available tools:
- add_expense: date (YYYY-MM-DD), amount (number), category (e.g. Food & Dining, Transportation, Shopping, Entertainment, Bills & Utilities, Healthcare, Travel, Education, Business, Other), subcategory (optional), note (optional)
- list_expenses: start_date (YYYY-MM-DD), end_date (YYYY-MM-DD)
- summarize: start_date (YYYY-MM-DD), end_date (YYYY-MM-DD), category (optional)

Guidelines:
- When the user asks to log/add an expense, identify the amount, category, date (default to today {today_str} if not specified), and note, then invoke `add_expense`.
- When asked to view or list expenses, call `list_expenses` with appropriate date range.
- When asked for totals or summary, call `summarize`.
- Format financial answers cleanly with currency symbols and markdown tables when appropriate.
- Be concise and friendly.
"""

# Initialize conversation history
if "history" not in st.session_state or not st.session_state.history:
    st.session_state.history = [SystemMessage(content=SYSTEM_PROMPT)]

if "tool_traces" not in st.session_state:
    st.session_state.tool_traces = {}

# Quick prompts for demo
demo_cols = st.columns(3)
with demo_cols[0]:
    if st.button("➕ Log Coffee Expense"):
        st.session_state.prompt_input = "Add an expense: $5.50 for Coffee at Starbucks under Food & Dining today."
with demo_cols[1]:
    if st.button("📋 List All My Expenses"):
        st.session_state.prompt_input = "Show me all expenses recorded for this month."
with demo_cols[2]:
    if st.button("📊 Summarize by Category"):
        st.session_state.prompt_input = "Summarize all my expenses by category for this year."

# ─────────────────────────────────────────────────────────────
# Render Existing Chat History
# ─────────────────────────────────────────────────────────────
for idx, msg in enumerate(st.session_state.history):
    if isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.markdown(msg.content)
    elif isinstance(msg, AIMessage):
        # Render assistant replies (excluding intermediate messages that only contained tool calls)
        if msg.content:
            with st.chat_message("assistant"):
                # Check if there are tool traces associated with this step
                if idx in st.session_state.tool_traces:
                    for trace in st.session_state.tool_traces[idx]:
                        with st.expander(f"🛠️ MCP Tool Call: `{trace['tool']}`", expanded=False):
                            st.json({"arguments": trace["args"], "result": trace["result"]})
                st.markdown(msg.content)

# ─────────────────────────────────────────────────────────────
# Handle User Input
# ─────────────────────────────────────────────────────────────
user_prompt = st.chat_input("Ask about or log your expenses...")

# Check for pre-filled demo prompt
if "prompt_input" in st.session_state and st.session_state.prompt_input:
    user_prompt = st.session_state.prompt_input
    st.session_state.prompt_input = None

if user_prompt:
    if not api_key:
        st.error("⚠️ GROQ_API_KEY is not configured in your `.env` file. Please check `.env`.")
        st.stop()
        
    if not st.session_state.get("server_connected", False):
        st.error("⚠️ Remote MCP Server is not reachable. Please check server URL and ensure test-remote-mcp-server is running.")
        st.stop()

    # Display user query
    with st.chat_message("user"):
        st.markdown(user_prompt)
    st.session_state.history.append(HumanMessage(content=user_prompt))

    # Initialize Groq LLM silently with backend credentials
    try:
        llm = ChatGroq(
            model=model_name,
            groq_api_key=api_key,
            temperature=0
        )
        llm_with_tools = llm.bind_tools(st.session_state.mcp_tools)
    except Exception as e:
        st.error(f"Failed to initialize language model: {e}")
        st.stop()

    # Invoke LLM with tool calling loop
    with st.chat_message("assistant"):
        with st.spinner("Processing..."):
            try:
                # 1) First pass: LLM decides whether to invoke tools
                first_reply = asyncio.run(llm_with_tools.ainvoke(st.session_state.history))
                tool_calls = getattr(first_reply, "tool_calls", None)

                if not tool_calls:
                    # Direct answer without tool call
                    st.markdown(first_reply.content or "")
                    st.session_state.history.append(first_reply)
                else:
                    # Append intermediate AIMessage with tool_calls
                    st.session_state.history.append(first_reply)
                    
                    traces = []
                    tool_messages = []
                    
                    # 2) Execute tools requested by the model
                    for tc in tool_calls:
                        tool_name = tc["name"]
                        args = tc.get("args") or {}
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except Exception:
                                pass
                        
                        tool_instance = st.session_state.tool_by_name.get(tool_name)
                        if tool_instance:
                            with st.status(f"Executing MCP tool `{tool_name}`...", expanded=True) as status:
                                st.write("Parameters:", args)
                                tool_result = asyncio.run(tool_instance.ainvoke(args))
                                st.write("Response from MCP server:", tool_result)
                                status.update(label=f"Completed `{tool_name}`", state="complete")
                            
                            traces.append({
                                "tool": tool_name,
                                "args": args,
                                "result": tool_result
                            })
                            tool_messages.append(
                                ToolMessage(
                                    tool_call_id=tc["id"],
                                    content=json.dumps(tool_result) if isinstance(tool_result, (dict, list)) else str(tool_result)
                                )
                            )
                        else:
                            tool_messages.append(
                                ToolMessage(
                                    tool_call_id=tc["id"],
                                    content=f"Error: Tool {tool_name} not found on MCP server."
                                )
                            )

                    # Append tool response messages
                    st.session_state.history.extend(tool_messages)

                    # 3) Final LLM pass: synthesize final response with tool outputs
                    final_reply = asyncio.run(llm.ainvoke(st.session_state.history))
                    st.markdown(final_reply.content or "")
                    
                    # Save reply and traces
                    reply_idx = len(st.session_state.history)
                    st.session_state.tool_traces[reply_idx] = traces
                    st.session_state.history.append(final_reply)

            except Exception as e:
                st.error(f"Error during execution: {e}")
