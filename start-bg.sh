#!/bin/bash

# Kimi API 监控服务后台启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PIDFILE="$SCRIPT_DIR/monitor.pid"
LOGFILE="$SCRIPT_DIR/monitor.log"
PYTHON_BIN="/home/ubuntu/miniforge3/bin/python3"

# 检查是否已在运行
if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "监控服务已在运行 (PID: $PID)"
        echo "查看日志: tail -f $LOGFILE"
        exit 0
    else
        rm -f "$PIDFILE"
    fi
fi

# 检查依赖
echo "检查依赖..."
if ! "$PYTHON_BIN" -c "import requests" >/dev/null 2>&1; then
    pip3 install requests -q 2>/dev/null || pip install requests -q 2>/dev/null
fi

echo "启动 Kimi API 监控服务 (后台模式)..."
# monitor.py 自己会写 LOGFILE。这里将 stdout/stderr 丢弃，避免日志重复写入。
nohup "$PYTHON_BIN" "$SCRIPT_DIR/monitor.py" --daemon > /dev/null 2>&1 &
PID=$!
echo $PID > "$PIDFILE"

# 启动后做一次存活检查，避免“已启动但秒退”
sleep 2
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "监控服务启动失败，请检查日志: $LOGFILE"
    rm -f "$PIDFILE"
    tail -n 20 "$LOGFILE" 2>/dev/null || true
    exit 1
fi

echo "监控服务已启动并在运行 (PID: $PID)"
echo "日志文件: $LOGFILE"
echo ""
echo "常用命令:"
echo "  查看日志:  tail -f $LOGFILE"
echo "  停止服务:  ./stop.sh"
echo "  单次检查:  python3 monitor.py --once"
echo "  模拟测试:  python3 monitor.py --simulate"
