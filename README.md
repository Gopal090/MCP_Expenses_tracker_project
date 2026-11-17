MCP Expense Tracker Project

A full-stack, end-to-end implementation of the **Model Context Protocol (MCP)** demonstrating how an LLM agent communicates with a remote MCP server to manage personal finances through an interactive Chatbot.

Architecture Overview

This project separates the **MCP Server** (tools, logic, database) and the **MCP Client** (LLM, prompt orchestration, frontend) using standard **Streamable HTTP transport**:

```
 ┌─────────────────────────────────────────────────────────┐
 │                  Streamlit Chatbot UI                   │
 │                  (mcp-client/app.py)                    │
 └────────────────────────────┬────────────────────────────┘
                              │
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │                   LangChain MCP Client                  │
 │          (MultiServerMCPClient + Groq LLM)              │
 └────────────────────────────┬────────────────────────────┘
                              │
                              │ Streamable HTTP (http://127.0.0.1:8000/mcp)
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │                  FastMCP Remote Server                  │
 │             (test-remote-mcp-server/main.py)            │
 └────────────────────────────┬────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
   [add_expense]       [list_expenses]        [summarize]
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
                     SQLite Database (expenses.db)
```

---

Key Features

- Remote MCP Server over HTTP**: Built with `FastMCP`, exposing tools asynchronously over Streamable HTTP on `0.0.0.0:8000`.
- Dynamic Tool Discovery**: The client connects over HTTP and automatically discovers all exposed MCP tools, their parameters, and types at runtime without hardcoded tool definitions.
- Groq LLM Integration**: Uses high-speed LLM inference (`openai/gpt-oss-120b`, `openai/gpt-oss-20b`, or `qwen/qwen3.8-27b`) via `langchain-groq` for natural language intent parsing and tool invocation.
- Streamlit Chatbot Frontend**:
  - Live MCP Server connection health indicator (🟢 Connected / 🔴 Offline).
  - Expandable MCP Tool execution badges revealing parameter payloads and server responses in real time.
  - One-click demo prompt buttons for quick testing.
  - Database Reset action to wipe records and start clean.
  - Secure credential handling (API keys are read silently from `.env` and never displayed in the UI).
- SQLite Persistence**: Maintains a durable database of expenses categorized by Date, Category, Subcategory, Amount, and Notes.

---



## 🛠️ MCP Tools Exposed by the Server

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `add_expense` | `date` (str), `amount` (float), `category` (str), `subcategory` (str, optional), `note` (str, optional) | Adds a new expense record to the database. |
| `list_expenses` | `start_date` (str), `end_date` (str) | Lists all expenses within an inclusive date range. |
| `summarize` | `start_date` (str), `end_date` (str), `category` (str, optional) | Returns total spending grouped by category with item counts. |

---

Getting Started

### 1. Prerequisites
- **Python 3.11+** installed
- **uv** (recommended for package management) or standard `pip`
- A free **Groq API Key** from [console.groq.com](https://console.groq.com)

### 2. Clone the Repository
```bash
git clone https://github.com/Gopal090/MCP_Expenses_tracker_project.git
cd MCP_Expenses_tracker_project
```

### 3. Setup Environment Variables
Create a `.env` file in the root directory (or copy from `.env.example`):
```bash
cp .env.example .env
```
Add your credentials:
```env
GROQ_API_KEY="your_groq_api_key_here"
MCP_SERVER_URL="http://127.0.0.1:8000/mcp"
```

### 4. Install Dependencies
**For the MCP Server:**
```bash
cd test-remote-mcp-server
uv sync
cd ..
```

**For the MCP Client:**
```bash
cd mcp-client
uv venv
uv pip install -r requirements.txt langchain-groq
cd ..
```

---

Running the Application

### Step 1: Start the Remote FastMCP Server
Run the batch file or script:
```powershell
.\run_server.bat
# Or in PowerShell:
.\run_server.ps1
```
*The server will start listening at `http://0.0.0.0:8000/mcp`.*

### Step 2: Start the Chatbot UI
In a separate terminal, launch the Streamlit frontend:
```powershell
.\run_chatbot.bat
# Or in PowerShell:
.\run_chatbot.ps1
```
*The chatbot will open in your browser at `http://localhost:8501`.*

---

## 💬 Example Queries to Try in the Chatbot

- **Add an expense:**
  > *"Log an expense of $45 for Dinner at Italian Bistro under Food & Dining today."*
  > *"Add $80 for electricity bill under Bills & Utilities on 2026-11-15."*

- **List expenses:**
  > *"Show all the expenses I recorded for this month."*
  > *"List my expenses between 2026-11-01 and 2026-11-30."*

- **Summarize spending:**
  > *"Summarize my expenses by category for this year."*
  > *"How much have I spent on Food & Dining so far?"*

---

