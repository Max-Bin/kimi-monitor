#!/bin/bash

# Kimi API 监控服务停止脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDFILE="$SCRIPT_DIR/monitor.pid"

if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "正在停止监控服务 (PID: $PID)..."
        kill "$PID"
        
        # 等待进程结束
        for i in {1..10}; do
            if ! ps -p "$PID" > /dev/null 2>&1; then
                echo "监控服务已停止"
                rm -f "$PIDFILE"
                exit 0
            fi
            sleep 1
        done
        
        # 强制终止
        echo "强制终止..."
        kill -9 "$PID" 2>/dev/null
        rm -f "$PIDFILE"
        echo "监控服务已停止"
    else
        echo "监控服务未运行"
        rm -f "$PIDFILE"
    fi
else
    echo "未找到 PID 文件，尝试查找进程..."
    PID=$(pgrep -f "python3.*monitor.py" | head -1)
    if [ -n "$PID" ]; then
        echo "找到进程 (PID: $PID)，正在停止..."
        kill "$PID"
        sleep 2
        echo "监控服务已停止"
    else
        echo "监控服务未运行"
    fi
fi
