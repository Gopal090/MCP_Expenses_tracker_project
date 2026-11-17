@echo off
echo Starting Remote FastMCP Expense Server on http://127.0.0.1:8000/mcp ...
cd test-remote-mcp-server
uv run python main.py
pause
