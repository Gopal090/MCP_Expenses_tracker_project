Write-Host "Starting Remote FastMCP Expense Server on http://127.0.0.1:8000/mcp ..." -ForegroundColor Cyan
Set-Location -Path "$PSScriptRoot\test-remote-mcp-server"
uv run python main.py
