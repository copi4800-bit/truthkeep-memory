# TruthKeep MCP Security Notes

TruthKeep Easy Mode chỉ phơi 5 tool memory chính. Đây là chủ ý bảo mật.

## Không có trong Easy Mode

- Shell execution.
- HTTP daemon.
- LAN/remote API.
- Cloud sync mặc định.
- Delete/export/destructive tools mặc định.
- Benchmark/dev/graph-debug tools mặc định.

## Vì sao cần giới hạn tool?

MCP server cho AI host quyền gọi tool. Tool càng nhiều, bề mặt lỗi càng lớn. Với TruthKeep, mục tiêu là làm memory chính, nên Easy Mode chỉ nên có thao tác memory an toàn.

## Advanced Mode

Advanced tools vẫn còn trong lõi, nhưng cần manifest riêng và user/dev bật rõ ràng.

## Structured errors

Tất cả lỗi nên tiến tới dạng:

```json
{
  "ok": false,
  "error": {
    "code": "DB_NOT_INITIALIZED",
    "message": "TruthKeep database is not initialized.",
    "fix": "Run: truthkeep easy install"
  }
}
```
