"""Kimi/Moonshot API 客户端"""

import requests
import logging
import json
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class UsageInfo:
    """用量信息"""
    # 本周用量
    weekly_usage_percent: float = 0.0  # 本周用量百分比
    weekly_reset_hours: float = 0.0    # 距离重置的小时数
    
    # 频率限制
    rate_limit_percent: float = 0.0    # 频率限制百分比
    rate_limit_reset_hours: float = 0.0  # 距离重置的小时数
    
    # 原始数据
    raw_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.raw_data is None:
            self.raw_data = {}


class KimiClient:
    """Kimi Code API 客户端"""
    
    BASE_URL = "https://api.kimi.com/coding/v1"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}"
        }
    
    def get_usage(self) -> Optional[UsageInfo]:
        """
        获取用量信息
        
        注意：Kimi Code API 目前没有官方的用量查询接口
        此功能保留用于未来 API 支持
        """
        logger.warning("Kimi Code API 暂不支持用量查询，请使用手动更新方式")
        return None
    
    def verify_key(self) -> bool:
        """验证 API Key 是否有效"""
        try:
            response = requests.get(
                f"{self.BASE_URL}/models",
                headers=self.headers,
                timeout=30
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"验证 API Key 失败: {e}")
            return False


class StateFileClient:
    """
    从状态文件读取用量信息的客户端
    适用于手动更新用量的场景
    """
    
    def __init__(self, state_file: str):
        self.state_file = state_file
    
    def get_usage(self) -> Optional[UsageInfo]:
        """从状态文件读取用量信息"""
        try:
            if not os.path.exists(self.state_file):
                logger.warning(f"状态文件不存在: {self.state_file}")
                return None
            
            with open(self.state_file, 'r') as f:
                data = json.load(f)
            
            return UsageInfo(
                weekly_usage_percent=data.get('weekly_last_percent', 0),
                weekly_reset_hours=data.get('weekly_last_reset_hours', 0),
                rate_limit_percent=data.get('rate_last_percent', 0),
                rate_limit_reset_hours=data.get('rate_last_last_reset_hours', 0),
                raw_data=data
            )
        except Exception as e:
            logger.error(f"读取状态文件失败: {e}")
            return None


class MockKimiClient:
    """
    模拟客户端，用于演示和测试
    """
    
    def __init__(self, weekly_percent: float = 13.0, 
                 weekly_reset_hours: float = 166.0,
                 rate_percent: float = 66.0,
                 rate_reset_hours: float = 3.0):
        self.weekly_percent = weekly_percent
        self.weekly_reset_hours = weekly_reset_hours
        self.rate_percent = rate_percent
        self.rate_reset_hours = rate_reset_hours
    
    def get_usage(self) -> UsageInfo:
        """获取模拟用量信息"""
        return UsageInfo(
            weekly_usage_percent=self.weekly_percent,
            weekly_reset_hours=self.weekly_reset_hours,
            rate_limit_percent=self.rate_percent,
            rate_limit_reset_hours=self.rate_reset_hours,
            raw_data={
                "source": "mock",
                "timestamp": datetime.now().isoformat()
            }
        )
    
    def simulate_countdown(self, minutes_elapsed: int = 10):
        """模拟时间流逝"""
        hours_elapsed = minutes_elapsed / 60.0
        self.weekly_reset_hours = max(0, self.weekly_reset_hours - hours_elapsed)
        self.rate_reset_hours = max(0, self.rate_reset_hours - hours_elapsed)
        
        # 如果重置时间到了，重置百分比
        if self.weekly_reset_hours <= 0:
            self.weekly_percent = 0.0
            self.weekly_reset_hours = 168.0  # 7天
        
        if self.rate_reset_hours <= 0:
            self.rate_percent = 0.0
            self.rate_reset_hours = 3.0  # 假设3小时周期
