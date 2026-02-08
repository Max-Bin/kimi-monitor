"""邮件通知模块"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailNotifier:
    """邮件通知器"""
    
    def __init__(self, smtp_server: str, smtp_port: int, 
                 smtp_user: str, smtp_password: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
    
    def send_notification(self, to_email: str, subject: str, body: str) -> bool:
        """发送邮件通知"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"邮件通知已发送至 {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"发送邮件失败: {e}")
            return False
    
    def send_quota_reset_notification(self, to_email: str, quota_type: str) -> bool:
        """发送配额重置通知"""
        subject = f"【Kimi API】{quota_type}已重置"
        
        body = f"""
您好！

您的 Kimi API {quota_type} 已重置为可用状态。

重置时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---
此邮件由 Kimi API 监控服务自动发送
"""
        return self.send_notification(to_email, subject, body)
    
    def send_both_reset_notification(self, to_email: str) -> bool:
        """发送两个配额都重置的通知"""
        subject = "【Kimi API】所有配额已重置"
        
        body = f"""
您好！

您的 Kimi API 配额已全部重置为可用状态：
✓ 本周用量已重置
✓ 频率限制已重置

重置时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

现在可以正常使用 API 了！

---
此邮件由 Kimi API 监控服务自动发送
"""
        return self.send_notification(to_email, subject, body)
    
    def send_status_report(self, to_email: str, weekly_percent: float,
                          weekly_reset_hours: float, rate_percent: float,
                          rate_reset_hours: float) -> bool:
        """发送状态报告"""
        subject = "【Kimi API】每日用量报告"
        
        weekly_reset_str = f"{weekly_reset_hours:.1f}小时"
        rate_reset_str = f"{rate_reset_hours:.1f}小时"
        
        body = f"""
Kimi API 用量状态报告

=== 本周用量 ===
使用率：{weekly_percent:.1f}%
重置时间：{weekly_reset_str}

=== 频率限制 ===
使用率：{rate_percent:.1f}%
重置时间：{rate_reset_str}

报告时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---
此邮件由 Kimi API 监控服务自动发送
"""
        return self.send_notification(to_email, subject, body)


class ConsoleNotifier:
    """控制台通知器（用于测试）"""
    
    def send_notification(self, to_email: str, subject: str, body: str) -> bool:
        """在控制台打印通知"""
        print(f"\n{'='*60}")
        print(f"【通知】{subject}")
        print(f"收件人: {to_email}")
        print(f"{'='*60}")
        print(body)
        print(f"{'='*60}\n")
        return True
    
    def send_quota_reset_notification(self, to_email: str, quota_type: str) -> bool:
        return self.send_notification(to_email, f"【Kimi API】{quota_type}已重置", 
                                      f"{quota_type} 已重置为可用状态")
    
    def send_both_reset_notification(self, to_email: str) -> bool:
        return self.send_notification(to_email, "【Kimi API】所有配额已重置",
                                      "本周用量和频率限制均已重置")
    
    def send_status_report(self, to_email: str, weekly_percent: float,
                          weekly_reset_hours: float, rate_percent: float,
                          rate_reset_hours: float) -> bool:
        body = f"""
本周用量: {weekly_percent:.1f}% (重置: {weekly_reset_hours:.1f}小时)
频率限制: {rate_percent:.1f}% (重置: {rate_reset_hours:.1f}小时)
"""
        return self.send_notification(to_email, "【Kimi API】用量报告", body)
