"""Kimi API 用量监控配置"""

import os
from dataclasses import dataclass


@dataclass
class Config:
    """配置类"""
    # Moonshot API Key (从 https://platform.moonshot.cn/ 获取)
    MOONSHOT_API_KEY: str = os.getenv("MOONSHOT_API_KEY", "")
    
    # 邮件配置 (使用 Gmail SMTP)
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")  # 发送方邮箱
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")  # 邮箱密码或应用专用密码
    
    # 通知邮箱
    NOTIFY_EMAIL: str = os.getenv("NOTIFY_EMAIL", "")
    
    # 检查间隔（分钟）
    CHECK_INTERVAL_MINUTES: int = int(os.getenv("CHECK_INTERVAL_MINUTES", "10"))
    
    # 状态文件路径
    STATE_FILE: str = os.getenv("STATE_FILE", "/home/ubuntu/kimi-monitor/state.json")
    
    # 日志文件路径
    LOG_FILE: str = os.getenv("LOG_FILE", "/home/ubuntu/kimi-monitor/monitor.log")


def load_config() -> Config:
    """加载配置"""
    # 尝试从配置文件加载
    config_path = "/home/ubuntu/kimi-monitor/config.json"
    if os.path.exists(config_path):
        import json
        with open(config_path, 'r') as f:
            config_dict = json.load(f)
        return Config(**config_dict)
    return Config()
