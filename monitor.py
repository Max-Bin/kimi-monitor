#!/usr/bin/env python3
"""
Kimi API 用量监控服务

监控内容：
- Weekly limit（84% left, resets in 6d 22h 54m）
- 5h limit（19% left, resets in 3h 54m）

当检测到重置后变成可用状态时，发送邮件通知
"""

import os
import sys
import time
import logging
import signal
from datetime import datetime, timedelta
from typing import Optional

from config import load_config, Config
from kimi_client import KimiClient, StateFileClient, MockKimiClient, UsageInfo
from kimi_code_client import MockKimiCodeClient, parse_usage_output
from notifier import EmailNotifier, ConsoleNotifier
from state_manager import StateManager


# 全局变量用于优雅退出
running = True


def setup_logging(log_file: str):
    """设置日志"""
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def signal_handler(signum, frame):
    """信号处理函数"""
    global running
    logging.info("收到终止信号，正在关闭...")
    running = False


def create_notifier(config: Config):
    """创建通知器"""
    # 如果没有配置 SMTP，使用控制台通知器（用于测试）
    if not config.SMTP_USER or not config.SMTP_PASSWORD:
        logging.warning("未配置 SMTP，使用控制台通知器")
        return ConsoleNotifier()
    
    return EmailNotifier(
        smtp_server=config.SMTP_SERVER,
        smtp_port=config.SMTP_PORT,
        smtp_user=config.SMTP_USER,
        smtp_password=config.SMTP_PASSWORD
    )


def create_client(config: Config):
    """创建 API 客户端"""
    # 优先使用状态文件客户端（从 update_usage.py 更新）
    if os.path.exists(config.STATE_FILE):
        logging.info("使用状态文件客户端")
        return StateFileClient(config.STATE_FILE)
    
    # 如果没有 API Key，使用 Kimi Code 模拟客户端
    if not config.MOONSHOT_API_KEY:
        logging.warning("未配置 MOONSHOT_API_KEY，使用 Kimi Code 模拟客户端")
        return MockKimiCodeClient()
    
    # 尝试使用 Kimi API 客户端
    client = KimiClient(api_key=config.MOONSHOT_API_KEY)
    if client.verify_key():
        return client
    
    logging.error("API Key 验证失败，使用模拟客户端")
    return MockKimiCodeClient()


def calculate_next_check_time(usage: UsageInfo) -> datetime:
    """
    计算下次检查时间
    在预计的重置时间后检查
    """
    now = datetime.now()
    
    # 找到最近的重置时间
    weekly_reset_time = now + timedelta(hours=usage.weekly_reset_hours)
    rate_reset_time = now + timedelta(hours=usage.rate_limit_reset_hours)
    
    # 在重置后 5 分钟检查
    weekly_check = weekly_reset_time + timedelta(minutes=5)
    rate_check = rate_reset_time + timedelta(minutes=5)
    
    # 取最近的一个
    if weekly_check < rate_check:
        return weekly_check
    return rate_check


def check_and_notify(client, notifier: EmailNotifier, state: StateManager,
                     config: Config) -> tuple[bool, Optional[datetime]]:
    """
    检查用量并发送通知
    返回: (检查成功, 下次检查时间)
    """
    try:
        # 获取用量信息
        usage = client.get_usage()
        if not usage:
            logging.error("无法获取用量信息")
            return False, None
        
        # 计算已用百分比（100 - left%）
        weekly_used = usage.weekly_usage_percent
        hourly_used = usage.rate_limit_percent
        
        logging.info(f"Weekly limit: {weekly_used:.1f}% 已用, "
                    f"重置: {usage.weekly_reset_hours:.1f}小时后")
        logging.info(f"5h limit: {hourly_used:.1f}% 已用, "
                    f"重置: {usage.rate_limit_reset_hours:.1f}小时后")
        
        # 检查是否发生重置
        weekly_reset = state.update_and_check_weekly(
            weekly_used,
            usage.weekly_reset_hours
        )
        
        rate_reset = state.update_and_check_rate(
            hourly_used,
            usage.rate_limit_reset_hours
        )
        
        # 发送通知
        notifications_sent = False
        
        if weekly_reset and rate_reset:
            # 两个都重置了
            logging.info("✓ 检测到两个配额都已重置，发送通知")
            if notifier.send_both_reset_notification(config.NOTIFY_EMAIL):
                state.mark_notified(weekly=True, rate=True)
                notifications_sent = True
        else:
            if weekly_reset:
                logging.info("✓ 检测到 Weekly limit 已重置，发送通知")
                if notifier.send_quota_reset_notification(
                    config.NOTIFY_EMAIL, "Weekly limit"
                ):
                    state.mark_notified(weekly=True)
                    notifications_sent = True
            
            if rate_reset:
                logging.info("✓ 检测到 5h limit 已重置，发送通知")
                if notifier.send_quota_reset_notification(
                    config.NOTIFY_EMAIL, "5h limit"
                ):
                    state.mark_notified(rate=True)
                    notifications_sent = True
        
        # 保存状态
        state.save_state()
        
        # 计算下次检查时间
        next_check = calculate_next_check_time(usage)
        logging.info(f"下次检查时间: {next_check.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True, next_check
        
    except Exception as e:
        logging.error(f"检查用量时出错: {e}")
        return False, None


def run_monitor(config: Optional[Config] = None):
    """运行监控服务"""
    global running
    
    if config is None:
        config = load_config()
    
    # 设置日志
    setup_logging(config.LOG_FILE)
    logger = logging.getLogger(__name__)
    
    logger.info("="*60)
    logger.info("Kimi API 用量监控服务启动")
    logger.info("="*60)
    logger.info(f"监控邮箱: {config.NOTIFY_EMAIL}")
    logger.info(f"基础检查间隔: {config.CHECK_INTERVAL_MINUTES}分钟")
    logger.info("="*60)
    
    # 创建组件
    client = create_client(config)
    notifier = create_notifier(config)
    state = StateManager(config.STATE_FILE)
    
    # 设置信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 主循环
    next_check_time = None
    
    while running:
        try:
            now = datetime.now()
            
            # 检查是否到了检查时间
            if next_check_time is None or now >= next_check_time:
                logger.info("开始检查用量...")
                success, next_check = check_and_notify(client, notifier, state, config)
                
                if success and next_check:
                    next_check_time = next_check
                    wait_seconds = (next_check - now).total_seconds()
                    
                    # 如果等待时间太长，最多等待配置的间隔
                    max_wait = config.CHECK_INTERVAL_MINUTES * 60
                    if wait_seconds > max_wait:
                        wait_seconds = max_wait
                        next_check_time = now + timedelta(seconds=max_wait)
                    
                    logger.info(f"下次检查: {next_check_time.strftime('%Y-%m-%d %H:%M:%S')} "
                              f"(约 {wait_seconds/60:.0f} 分钟后)")
                else:
                    # 检查失败，使用默认间隔
                    next_check_time = now + timedelta(minutes=config.CHECK_INTERVAL_MINUTES)
                    logger.info(f"检查失败，{config.CHECK_INTERVAL_MINUTES}分钟后重试")
            else:
                # 显示下次检查倒计时
                wait_seconds = (next_check_time - now).total_seconds()
                if wait_seconds < 60:  # 最后60秒每秒显示
                    logger.debug(f"距离下次检查: {wait_seconds:.0f}秒")
            
        except Exception as e:
            logger.error(f"检查过程中出错: {e}")
            next_check_time = datetime.now() + timedelta(minutes=config.CHECK_INTERVAL_MINUTES)
        
        # 等待下一次检查（每秒检查一次是否该退出）
        waited = 0
        check_interval = 1  # 每秒检查一次
        
        while running:
            now = datetime.now()
            if next_check_time and now >= next_check_time:
                break
            
            time.sleep(check_interval)
            waited += check_interval
            
            # 每分钟记录一次日志
            if waited % 60 == 0 and next_check_time:
                remaining = (next_check_time - datetime.now()).total_seconds()
                if remaining > 60:
                    logger.debug(f"距离下次检查还有 {remaining/60:.0f} 分钟")
    
    logger.info("监控服务已停止")


def run_once(config: Optional[Config] = None):
    """运行一次检查（用于测试）"""
    if config is None:
        config = load_config()
    
    setup_logging(config.LOG_FILE)
    
    client = create_client(config)
    notifier = create_notifier(config)
    state = StateManager(config.STATE_FILE)
    
    print("\n" + "="*60)
    print("运行单次检查")
    print("="*60)
    
    success, next_check = check_and_notify(client, notifier, state, config)
    
    print("="*60)
    if success and next_check:
        print(f"下次建议检查时间: {next_check.strftime('%Y-%m-%d %H:%M:%S')}")


def simulate_test():
    """模拟测试 - 模拟时间流逝和重置"""
    config = load_config()
    setup_logging(config.LOG_FILE)
    
    # 使用 Kimi Code 模拟客户端
    from kimi_code_client import MockKimiCodeClient
    client = MockKimiCodeClient()
    
    # 模拟即将重置的状态
    client.weekly_left = 5.0  # 几乎用完
    client.weekly_reset_hours = 0.05  # 3分钟后重置
    client.hourly_left = 5.0
    client.hourly_reset_hours = 0.05
    
    notifier = create_notifier(config)
    state = StateManager(config.STATE_FILE)
    
    print("\n" + "="*60)
    print("模拟测试模式 - 模拟重置过程")
    print("="*60)
    
    for i in range(8):
        print(f"\n--- 第 {i+1} 次检查 ---")
        print(f"当前状态: Weekly {100-client.weekly_left:.0f}% 已用, "
              f"5h {100-client.hourly_left:.0f}% 已用")
        
        check_and_notify(client, notifier, state, config)
        
        # 模拟时间流逝（每次 2 分钟）
        client.simulate_countdown(minutes=2)
        
        # 在第五次检查时模拟重置
        if i == 4:
            client.weekly_left = 100.0
            client.hourly_left = 100.0
            print("*** 模拟重置发生 ***")
    
    print("\n" + "="*60)
    print("模拟测试完成")
    print("="*60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Kimi API 用量监控服务")
    parser.add_argument("--once", action="store_true", 
                       help="运行一次检查然后退出")
    parser.add_argument("--simulate", action="store_true",
                       help="运行模拟测试")
    parser.add_argument("--daemon", action="store_true",
                       help="以守护进程模式运行（持续监控）")
    
    args = parser.parse_args()
    
    if args.simulate:
        simulate_test()
    elif args.once:
        run_once()
    else:
        # 默认以守护进程模式运行
        run_monitor()
