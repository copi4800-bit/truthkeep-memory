# MCP Host Profiles

TruthKeep dùng profile để sinh config đúng dạng nhất có thể cho từng host.

## Supported profiles

```text
openclaw
claude
cursor
cline
roo
continue
vscode
generic
```

## Lệnh chung

```bash
truthkeep mcp config <host>
truthkeep mcp install <host>
truthkeep mcp doctor <host>
truthkeep mcp smoke-test <host>
```

## Target path thủ công

Nếu host dùng đường dẫn config riêng, dùng:

```bash
truthkeep mcp install <host> --target /path/to/config.json
truthkeep mcp doctor <host> --target /path/to/config.json
```

## Không mở port

Tất cả profile mặc định dùng:

```json
{
  "command": "truthkeep-mcp",
  "args": [],
  "env": {
    "TRUTHKEEP_MODE": "easy",
    "TRUTHKEEP_TRANSPORT": "stdio",
    "TRUTHKEEP_OPEN_PORTS": "0"
  }
}
```
