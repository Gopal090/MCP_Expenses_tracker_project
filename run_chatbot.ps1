Write-Host "Starting Streamlit MCP Chatbot Frontend..." -ForegroundColor Cyan
Set-Location -Path "$PSScriptRoot\mcp-client"
& ".\.venv\Scripts\streamlit.exe" run app.py
