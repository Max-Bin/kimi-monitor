#!/bin/bash

# Kimi API 监控服务状态检查脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDFILE="$SCRIPT_DIR/monitor.pid"
LOGFILE="$SCRIPT_DIR/monitor.log"
STATEFILE="$SCRIPT_DIR/state.json"

echo "=== Kimi API 监控服务状态 ==="
echo ""

# 检查进程状态
if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "✓ 服务运行中 (PID: $PID)"
    else
        echo "✗ 服务未运行 (PID 文件存在但进程不存在)"
    fi
else
    PID=$(pgrep -f "python3.*monitor.py" | head -1)
    if [ -n "$PID" ]; then
        echo "✓ 服务运行中 (PID: $PID)"
    else
        echo "✗ 服务未运行"
    fi
fi

echo ""
echo "文件位置:"
echo "  日志文件: $LOGFILE"
echo "  状态文件: $STATEFILE"
echo "  PID 文件: $PIDFILE"

# 显示最近日志
if [ -f "$LOGFILE" ]; then
    echo ""
    echo "最近日志 (最后10行):"
    echo "---"
    tail -10 "$LOGFILE"
fi

# 显示状态
if [ -f "$STATEFILE" ]; then
    echo ""
    echo "当前状态:"
    echo "---"
    cat "$STATEFILE"
fi

echo ""
echo "=== 结束 ==="
