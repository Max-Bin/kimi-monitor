#!/usr/bin/env python3
"""
手动更新 Kimi API 用量工具

当你运行 `kimi` 后输入 `/usage` 看到如下输出时：
╭────────────────────────────── API Usage ───────────────────────────────╮
│  Weekly limit  ━━━╺━━━━━━━━━━━━━━━━  84% left  (resets in 6d 22h 54m)  │
│  5h limit      ━━━━━━━━━━━━━━━━╺━━━  19% left  (resets in 3h 54m)      │
╰────────────────────────────────────────────────────────────────────────╯

运行此脚本更新监控状态：
  ./update_usage.py 84 6 22 54 19 3 54

参数说明：
  - 84: Weekly limit 剩余 %
  - 6 22 54: 重置时间 6天 22小时 54分钟
  - 19: 5h limit 剩余 %
  - 3 54: 重置时间 3小时 54分钟
"""

import json
import sys
import os
from datetime import datetime

STATE_FILE = "/home/ubuntu/kimi-monitor/state.json"


def load_state():
    """加载状态"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {
        "weekly_was_full": False,
        "weekly_last_percent": 0.0,
        "weekly_last_reset_hours": 0.0,
        "rate_was_full": False,
        "rate_last_percent": 0.0,
        "rate_last_last_reset_hours": 0.0,
        "weekly_reset_notified": False,
        "rate_reset_notified": False
    }


def save_state(state):
    """保存状态"""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def update_usage(weekly_left, weekly_days, weekly_hours, weekly_mins,
                 hourly_left, hourly_hours, hourly_mins):
    """
    更新用量信息
    
    Args:
        weekly_left: Weekly limit 剩余百分比 (如 84)
        weekly_days: 重置剩余天数
        weekly_hours: 重置剩余小时数
        weekly_mins: 重置剩余分钟数
        hourly_left: 5h limit 剩余百分比 (如 19)
        hourly_hours: 重置剩余小时数
        hourly_mins: 重置剩余分钟数
    """
    state = load_state()
    
    # 转换为已用百分比
    weekly_used = 100 - weekly_left
    hourly_used = 100 - hourly_left
    
    # 计算重置时间（小时）
    weekly_reset_hours = weekly_days * 24 + weekly_hours + weekly_mins / 60
    hourly_reset_hours = hourly_hours + hourly_mins / 60
    
    # 保存旧值用于检测重置
    old_weekly_pct = state.get("weekly_last_percent", 0)
    old_weekly_reset = state.get("weekly_last_reset_hours", 168)
    old_rate_pct = state.get("rate_last_percent", 0)
    old_rate_reset = state.get("rate_last_last_reset_hours", 3)
    
    # 检测是否发生重置
    weekly_reset_detected = False
    rate_reset_detected = False
    
    # 本周用量重置检测
    if old_weekly_pct > 80 and weekly_used < 20:
        weekly_reset_detected = True
        print(f"✓ 检测到 Weekly limit 重置: {old_weekly_pct:.1f}% -> {weekly_used:.1f}%")
    elif old_weekly_reset < 1 and weekly_reset_hours > 160:
        weekly_reset_detected = True
        print(f"✓ 检测到 Weekly limit 重置: 重置时间 {old_weekly_reset:.1f}h -> {weekly_reset_hours:.1f}h")
    
    # 频率限制重置检测
    if old_rate_pct > 80 and hourly_used < 20:
        rate_reset_detected = True
        print(f"✓ 检测到 5h limit 重置: {old_rate_pct:.1f}% -> {hourly_used:.1f}%")
    elif old_rate_reset < 0.5 and hourly_reset_hours > 2:
        rate_reset_detected = True
        print(f"✓ 检测到 5h limit 重置: 重置时间 {old_rate_reset:.1f}h -> {hourly_reset_hours:.1f}h")
    
    # 更新状态
    state["weekly_last_percent"] = weekly_used
    state["weekly_last_reset_hours"] = weekly_reset_hours
    state["weekly_was_full"] = weekly_used > 80
    
    state["rate_last_percent"] = hourly_used
    state["rate_last_last_reset_hours"] = hourly_reset_hours
    state["rate_was_full"] = hourly_used > 70
    
    state["last_check_time"] = datetime.now().isoformat()
    
    # 如果检测到重置，重置通知标志
    if weekly_reset_detected:
        state["weekly_reset_notified"] = False
    if rate_reset_detected:
        state["rate_reset_notified"] = False
    
    save_state(state)
    
    print(f"\n用量信息已更新:")
    print(f"  Weekly limit: {weekly_used}% 已用 ({weekly_left}% 剩余)")
    print(f"                重置: {weekly_days}天 {weekly_hours}小时 {weekly_mins}分钟")
    print(f"  5h limit:     {hourly_used}% 已用 ({hourly_left}% 剩余)")
    print(f"                重置: {hourly_hours}小时 {hourly_mins}分钟")
    
    if weekly_reset_detected or rate_reset_detected:
        print(f"\n⚠ 检测到配额重置，启动监控服务将发送通知")
        return True
    
    # 计算下次检查时间
    weekly_reset_time = weekly_reset_hours
    hourly_reset_time = hourly_reset_hours
    
    print(f"\n预计检查时间:")
    print(f"  Weekly limit: {weekly_reset_time:.1f}小时后")
    print(f"  5h limit:     {hourly_reset_time:.1f}小时后")
    
    return False


def show_current():
    """显示当前状态"""
    state = load_state()
    
    weekly_used = state.get('weekly_last_percent', 0)
    hourly_used = state.get('rate_last_percent', 0)
    
    print("当前监控状态:")
    print(f"  Weekly limit: {weekly_used}% 已用 ({100-weekly_used}% 剩余)")
    print(f"                重置: {state.get('weekly_last_reset_hours', 0):.1f}小时后")
    print(f"  5h limit:     {hourly_used}% 已用 ({100-hourly_used}% 剩余)")
    print(f"                重置: {state.get('rate_last_last_reset_hours', 0):.1f}小时后")
    print(f"  上次更新: {state.get('last_check_time', '从未')}")


def main():
    if len(sys.argv) == 1:
        print(__doc__)
        print("\n当前状态:")
        print("-" * 50)
        show_current()
        sys.exit(0)
    
    if sys.argv[1] in ("--show", "-s"):
        show_current()
        sys.exit(0)
    
    if len(sys.argv) != 8:
        print("错误: 需要7个参数")
        print("")
        print("用法:")
        print("  ./update_usage.py <weekly_left> <weekly_d> <weekly_h> <weekly_m> \\")
        print("                    <hourly_left> <hourly_h> <hourly_m>")
        print("")
        print("示例 (对应: 84% left, resets in 6d 22h 54m / 19% left, resets in 3h 54m):")
        print("  ./update_usage.py 84 6 22 54 19 3 54")
        sys.exit(1)
    
    try:
        args = [float(x) for x in sys.argv[1:8]]
        
        if update_usage(*args):
            print("\n建议运行以下命令启动监控:")
            print("  cd /home/ubuntu/kimi-monitor && ./start-bg.sh")
        
    except ValueError as e:
        print(f"错误: 参数必须是数字 - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
