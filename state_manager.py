"""状态管理模块"""

import json
import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MonitorState:
    """监控状态"""
    # 本周用量状态
    weekly_was_full: bool = False  # 之前是否已满（接近100%）
    weekly_last_percent: float = 0.0
    weekly_last_reset_hours: float = 0.0
    
    # 频率限制状态
    rate_was_full: bool = False
    rate_last_percent: float = 0.0
    rate_last_last_reset_hours: float = 0.0
    
    # 上次检查时间
    last_check_time: Optional[str] = None
    
    # 重置通知已发送
    weekly_reset_notified: bool = False
    rate_reset_notified: bool = False


class StateManager:
    """状态管理器"""
    
    def __init__(self, state_file: str):
        self.state_file = state_file
        self.state = self._load_state()
    
    def _load_state(self) -> MonitorState:
        """从文件加载状态"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                return MonitorState(**data)
            except Exception as e:
                logger.error(f"加载状态文件失败: {e}")
        return MonitorState()
    
    def save_state(self):
        """保存状态到文件"""
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(asdict(self.state), f, indent=2)
        except Exception as e:
            logger.error(f"保存状态文件失败: {e}")
    
    def update_and_check_weekly(self, current_percent: float, 
                                reset_hours: float) -> bool:
        """
        更新本周用量状态并检查是否发生了重置
        返回 True 表示检测到了重置事件
        """
        was_full = self.state.weekly_was_full
        last_percent = self.state.weekly_last_percent
        last_reset_hours = self.state.weekly_last_reset_hours
        
        # 检测重置：如果之前用量高(>80%)，现在用量低(<20%)，或者重置时间增加了
        is_reset = False
        
        if was_full and current_percent < 20:
            # 从高用量降到低用量，说明重置了
            is_reset = True
            logger.info(f"检测到本周用量重置: {last_percent:.1f}% -> {current_percent:.1f}%")
        elif last_reset_hours < 1 and reset_hours > 160:
            # 重置时间从接近0变回约168小时，说明重置了
            is_reset = True
            logger.info(f"检测到本周用量重置: 重置时间 {last_reset_hours:.1f}h -> {reset_hours:.1f}h")
        elif last_percent > 90 and current_percent < last_percent - 50:
            # 用量大幅下降（超过50%），说明重置了
            is_reset = True
            logger.info(f"检测到本周用量重置: 用量大幅下降 {last_percent:.1f}% -> {current_percent:.1f}%")
        
        # 更新状态
        self.state.weekly_last_percent = current_percent
        self.state.weekly_last_reset_hours = reset_hours
        self.state.weekly_was_full = current_percent > 80
        self.state.last_check_time = datetime.now().isoformat()
        
        if is_reset:
            self.state.weekly_reset_notified = False
        
        return is_reset and not self.state.weekly_reset_notified
    
    def update_and_check_rate(self, current_percent: float,
                              reset_hours: float) -> bool:
        """
        更新频率限制状态并检查是否发生了重置
        返回 True 表示检测到了重置事件
        """
        was_full = self.state.rate_was_full
        last_percent = self.state.rate_last_percent
        last_reset_hours = self.state.rate_last_last_reset_hours
        
        # 检测重置
        is_reset = False
        
        if was_full and current_percent < 20:
            is_reset = True
            logger.info(f"检测到频率限制重置: {last_percent:.1f}% -> {current_percent:.1f}%")
        elif last_reset_hours < 0.5 and reset_hours > 2:
            # 重置时间从接近0变回约3小时，说明重置了
            is_reset = True
            logger.info(f"检测到频率限制重置: 重置时间 {last_reset_hours:.1f}h -> {reset_hours:.1f}h")
        elif last_percent > 80 and current_percent < last_percent - 40:
            is_reset = True
            logger.info(f"检测到频率限制重置: 用量大幅下降 {last_percent:.1f}% -> {current_percent:.1f}%")
        
        # 更新状态
        self.state.rate_last_percent = current_percent
        self.state.rate_last_last_reset_hours = reset_hours
        self.state.rate_was_full = current_percent > 70
        self.state.last_check_time = datetime.now().isoformat()
        
        if is_reset:
            self.state.rate_reset_notified = False
        
        return is_reset and not self.state.rate_reset_notified
    
    def mark_notified(self, weekly: bool = False, rate: bool = False):
        """标记已发送通知"""
        if weekly:
            self.state.weekly_reset_notified = True
        if rate:
            self.state.rate_reset_notified = True
        self.save_state()
