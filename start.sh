#!/bin/bash

# Kimi API 监控服务启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python3"
    exit 1
fi

# 检查依赖
echo "检查依赖..."
pip3 install requests -q 2>/dev/null || pip install requests -q 2>/dev/null

echo "启动 Kimi API 监控服务..."
echo "日志文件: $SCRIPT_DIR/monitor.log"
echo ""
echo "使用方式:"
echo "  1. 守护进程模式: ./start.sh"
echo "  2. 单次检查:     /home/ubuntu/miniforge3/bin/python3 monitor.py --once"
echo "  3. 模拟测试:     python3 monitor.py --simulate"
echo ""
echo "按 Ctrl+C 停止服务"
echo "---"

# 运行监控服务
python3 monitor.py --daemon 2>&1 | tee -a "$SCRIPT_DIR/monitor.log"
