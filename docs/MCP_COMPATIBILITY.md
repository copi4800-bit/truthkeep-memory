# TruthKeep MCP Compatibility Matrix

| Host | Profile status | Install command | Notes |
|---|---:|---|---|
| OpenClaw | tested-profile | `truthkeep mcp install openclaw` | Easy Mode manifest with 5 memory tools. |
| Claude Desktop | config-profile | `truthkeep mcp install claude` | Writes/merges `mcpServers.truthkeep` where profile path is available. Needs real-host validation on each OS. |
| Cursor | config-profile | `truthkeep mcp install cursor` | Writes/merges `.cursor/mcp.json` style config when available. Needs real-host validation. |
| Cline | generated-config | `truthkeep mcp install cline` | Writes generated MCP config under `~/.truthkeep/mcp/` unless target path is provided. |
| Roo Code | generated-config | `truthkeep mcp install roo` | Writes generated MCP config under `~/.truthkeep/mcp/` unless target path is provided. |
| Continue | generated-config | `truthkeep mcp install continue` | Writes generated MCP config under `~/.truthkeep/mcp/` unless target path is provided. |
| VS Code MCP host | generated-config | `truthkeep mcp install vscode` | Generic VS Code-compatible MCP config. |
| Generic | supported | `truthkeep mcp install generic` | Portable `mcpServers` JSON for copy-paste use. |

## Trạng thái thật

Bản này là **MCP Universal profile layer**, không phải bảo chứng mọi host đã được test GUI thật. Mỗi host cần real-machine validation vì mỗi app có thể đổi đường dẫn config hoặc cơ chế reload.
