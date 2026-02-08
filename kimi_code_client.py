"""
Kimi Code CLI 客户端
通过调用本地 kimi code 命令获取用量信息
"""

import subprocess
import re
import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta
from kimi_client import UsageInfo

logger = logging.getLogger(__name__)


class KimiCodeCLIClient:
    """通过 Kimi Code CLI 获取用量信息"""
    
    def __init__(self, work_dir: str = "/home/ubuntu"):
        self.work_dir = work_dir
        self.kimi_path = "/home/ubuntu/.local/bin/kimi"
    
    def _run_kimi_command(self, command: str) -> Optional[str]:
        """运行 kimi 命令并获取输出"""
        try:
            # 创建一个临时 expect 脚本来自动化交互
            expect_script = f'''#!/usr/bin/env expect -f
set timeout 5
spawn {self.kimi_path} -w {self.work_dir} -p "{command}"
expect {{
    eof {{ exit 0 }}
    timeout {{ exit 1 }}
}}
'''
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.exp', delete=False) as f:
                f.write(expect_script)
                exp_file = f.name
            
            os.chmod(exp_file, 0o755)
            
            result = subprocess.run(
                ["expect", exp_file],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            os.unlink(exp_file)
            
            if result.returncode == 0:
                return result.stdout + result.stderr
            else:
                logger.error(f"kimi 命令失败: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"运行 kimi 命令失败: {e}")
            return None
    
    def get_usage_from_session(self) -> Optional[UsageInfo]:
        """
        从已有的 kimi 会话日志中获取用量信息
        或者通过直接读取 ~/.kimi 目录下的信息
        """
        # 尝试从 wire.jsonl 文件中查找用量信息
        import os
        import json
        
        sessions_dir = "/home/ubuntu/.kimi/sessions"
        if not os.path.exists(sessions_dir):
            return None
        
        # 查找最新的会话
        latest_wire = None
        latest_time = 0
        
        for root, dirs, files in os.walk(sessions_dir):
            for file in files:
                if file == "wire.jsonl":
                    filepath = os.path.join(root, file)
                    mtime = os.path.getmtime(filepath)
                    if mtime > latest_time:
                        latest_time = mtime
                        latest_wire = filepath
        
        if not latest_wire:
            return None
        
        # 从 wire.jsonl 中查找用量信息
        try:
            with open(latest_wire, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        # 查找包含用量的消息
                        if 'usage' in data or 'quota' in str(data).lower():
                            # 解析用量信息
                            pass
                    except:
                        continue
        except Exception as e:
            logger.error(f"读取会话文件失败: {e}")
        
        return None


class MockKimiCodeClient:
    """
    模拟 Kimi Code 用量输出
    用于演示和测试
    """
    
    # 模拟状态
    weekly_left = 84.0  # 剩余百分比
    weekly_reset_hours = 6 * 24 + 22 + 54/60  # 6d 22h 54m
    
    hourly_left = 19.0  # 剩余百分比 (5h limit)
    hourly_reset_hours = 3 + 54/60  # 3h 54m
    
    def __init__(self):
        pass
    
    def get_usage(self) -> UsageInfo:
        """获取用量信息"""
        # 将剩余百分比转换为已用百分比
        weekly_used = 100 - self.weekly_left
        hourly_used = 100 - self.hourly_left
        
        return UsageInfo(
            weekly_usage_percent=weekly_used,
            weekly_reset_hours=self.weekly_reset_hours,
            rate_limit_percent=hourly_used,
            rate_limit_reset_hours=self.hourly_reset_hours,
            raw_data={
                "source": "kimi_code_mock",
                "weekly_left": self.weekly_left,
                "hourly_left": self.hourly_left,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    def simulate_countdown(self, minutes: float = 10):
        """模拟时间流逝"""
        hours = minutes / 60.0
        
        self.weekly_reset_hours = max(0, self.weekly_reset_hours - hours)
        self.hourly_reset_hours = max(0, self.hourly_reset_hours - hours)
        
        # 如果重置时间到了，重置百分比
        if self.weekly_reset_hours <= 0:
            self.weekly_left = 100.0
            self.weekly_reset_hours = 7 * 24  # 7天
            logger.info("模拟: 本周用量已重置")
        
        if self.hourly_reset_hours <= 0:
            self.hourly_left = 100.0
            self.hourly_reset_hours = 5  # 5小时
            logger.info("模拟: 5小时限制已重置")


def parse_usage_output(output: str) -> Optional[UsageInfo]:
    """
    解析 kimi code /usage 命令的输出
    
    示例输出:
    ╭────────────────────────────── API Usage ───────────────────────────────╮
    │  Weekly limit  ━━━╺━━━━━━━━━━━━━━━━  84% left  (resets in 6d 22h 54m)  │
    │  5h limit      ━━━━━━━━━━━━━━━━╺━━━  19% left  (resets in 3h 54m)      │
    ╰────────────────────────────────────────────────────────────────────────╯
    """
    try:
        # 解析 Weekly limit
        weekly_match = re.search(
            r'Weekly limit.*?(\d+)% left.*?resets in (\d+)d (\d+)h (\d+)m',
            output, re.DOTALL
        )
        
        # 解析 5h limit
        hourly_match = re.search(
            r'5h limit.*?(\d+)% left.*?resets in (\d+)h (\d+)m',
            output, re.DOTALL
        )
        
        if not weekly_match or not hourly_match:
            logger.error("无法解析用量输出")
            return None
        
        # 提取 Weekly 数据
        weekly_left = float(weekly_match.group(1))
        weekly_days = int(weekly_match.group(2))
        weekly_hours = int(weekly_match.group(3))
        weekly_mins = int(weekly_match.group(4))
        weekly_reset_hours = weekly_days * 24 + weekly_hours + weekly_mins / 60
        
        # 提取 Hourly 数据
        hourly_left = float(hourly_match.group(1))
        hourly_hours = int(hourly_match.group(2))
        hourly_mins = int(hourly_match.group(3))
        hourly_reset_hours = hourly_hours + hourly_mins / 60
        
        return UsageInfo(
            weekly_usage_percent=100 - weekly_left,  # 转换为已用百分比
            weekly_reset_hours=weekly_reset_hours,
            rate_limit_percent=100 - hourly_left,  # 转换为已用百分比
            rate_limit_reset_hours=hourly_reset_hours,
            raw_data={
                "source": "kimi_code_cli",
                "weekly_left": weekly_left,
                "hourly_left": hourly_left
            }
        )
        
    except Exception as e:
        logger.error(f"解析用量输出失败: {e}")
        return None


# 测试
if __name__ == "__main__":
    # 测试解析功能
    test_output = """
╭────────────────────────────── API Usage ───────────────────────────────╮
│  Weekly limit  ━━━╺━━━━━━━━━━━━━━━━  84% left  (resets in 6d 22h 54m)  │
│  5h limit      ━━━━━━━━━━━━━━━━╺━━━  19% left  (resets in 3h 54m)      │
╰────────────────────────────────────────────────────────────────────────╯
"""
    
    usage = parse_usage_output(test_output)
    if usage:
        print(f"本周用量: {usage.weekly_usage_percent:.1f}% (重置: {usage.weekly_reset_hours:.1f}小时)")
        print(f"5h限制: {usage.rate_limit_percent:.1f}% (重置: {usage.rate_limit_reset_hours:.1f}小时)")
    else:
        print("解析失败")
