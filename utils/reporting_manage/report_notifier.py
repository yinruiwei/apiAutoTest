from pathlib import Path
from typing import Any

from config.settings import settings
from utils.logger import log

from utils.reporting_manage.send_email import email_notifier
from utils.reporting_manage.send_dingding import dingding_notifier

__all__ = ["notify_mgr"]


class NotificationManager:
    """全局消息通知调度中心"""

    def send_all_notifications(self, summary_data: dict[str, Any], report_file: Path | None = None) -> None:
        """
        统一的消息分发入口。
        """
        log.info("📢 开始执行测试结果推送调度...")

        # 邮件推送
        if settings.email.send:
            log.info("✅ 邮件推送开关已开启，准备发送...")
            self._safe_execute(email_notifier.send_report, summary_data, attach_file=report_file)
        else:
            log.info("⏭️ 邮件推送开关已关闭 (settings.email.send=False)")

        # 2. 钉钉推送
        if settings.notify.dingding.send:
            log.info("✅ 钉钉推送开关已开启，准备发送...")
            self._safe_execute(dingding_notifier.send_report, summary_data)
        else:
            log.info("⏭️ 钉钉推送开关已关闭 (settings.notify.dingding.send=False)")

        # 3. 飞书推送 (预留，后续只需增加 feishu.send 配置即可在此扩展)
        log.info("🏁 消息推送调度执行完毕。")

    def _safe_execute(self, func, *args, **kwargs):
        """
        异常隔离器：
        保证任意一个推送渠道（如邮件服务器挂了）失败时，不会导致整个调度过程崩溃，
        确保其他渠道（如钉钉）依然能够正常尝试发送。
        """
        try:
            func(*args, **kwargs)
        except Exception as e:
            # 动态获取函数名，方便在日志中准确定位报错的通道
            channel_name = getattr(func, "__name__", str(func))
            log.error(f"❌ 推送通道 [{channel_name}] 执行失败: {e}")


# 暴露单例，供 conftest.py 调用
notify_mgr = NotificationManager()