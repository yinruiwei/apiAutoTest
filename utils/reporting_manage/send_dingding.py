import base64
import hashlib
import hmac
import time
import urllib.parse
from typing import Any

import httpx

from config.settings import settings
from utils.logger import log

__all__ = ['dingding_notifier']


class DingTalkNotifier:
    """钉钉群机器人 Webhook 推送引擎"""

    def __init__(self):
        self.conf = settings.notify.dingding

    def _get_signed_url(self) -> str:
        """
        生成加签后的 Webhook URL
        对应 Shell 脚本中的 openssl dgst -sha256 -hmac 逻辑
        """
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.conf.secret.encode('utf-8')
        string_to_sign = f'{timestamp}\n{self.conf.secret}'
        string_to_sign_enc = string_to_sign.encode('utf-8')

        # 1. HMAC-SHA256 加密
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()

        # 2. Base64 编码
        # 3. URL 编码 (quote_plus)
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

        # 拼接最终请求地址
        return f'{self.conf.webhook}&timestamp={timestamp}&sign={sign}'

    def _generate_markdown(self, summary: dict[str, Any]) -> dict[str, Any]:
        """组装钉钉的 Markdown 报文 """
        result_status = summary['result']

        total = summary.get('total', 0)
        passed = summary.get('passed', 0)
        failed = summary.get('failed', 0)
        error = summary.get('error', 0)
        skipped = summary.get('skipped', 0)

        pass_rate = f'{(passed / total * 100):.2f}%' if total > 0 else '0.00%'

        if result_status == 'Success':
            theme_color = '#159811'  # 护眼绿
            status_text = '🎉 测试通过 (Success)'
        else:
            theme_color = '#d32f2f'  # 警示红
            status_text = '🚨 发现异常 (Failed/Error)'

        # 处理关键字前缀
        kw_prefix = f'【{self.conf.secret}】' if self.conf.secret_type == 'keywords' and self.conf.secret else ''
        title_str = f'{(kw_prefix + " ") if kw_prefix else ""}{settings.report.title}'

        run_env = summary.get('run_env', '')
        runner_host = summary.get('runner_host', '')
        target_hosts = summary.get('target_hosts') or {}
        target_line = '、'.join(f'{k.removeprefix("Target.")}={v}' for k, v in target_hosts.items()) or '-'
        report_url = summary.get('allure_report_url') or ''

        # 核心改动：使用多行 f-string 配合 \n\n，严控 <font> 的边界，避免颜色污染
        text = f"""### {title_str}

**<font color="{theme_color}">{status_text}</font>**

---

**运行环境**：{run_env or '-'} | **执行机**：{runner_host or '-'}

**被测服务**：{target_line}

**任务说明**：{settings.report.tester_name}

**开始时间**：{summary['started_time']}

**运行耗时**：{summary['elapsed_time']}

**通过率**：**<font color="{theme_color}">{pass_rate}</font>**

---

#### 📊 核心数据统计

- 总用例数：**{total}**
- 通过 (Pass)：<font color="#159811">{passed}</font>
- 失败 (Fail)：<font color="#d32f2f">{failed}</font>
- 错误 (Error)：<font color="#d32f2f">{error}</font>
- 跳过 (Skip)：<font color="#f57c00">{skipped}</font>

---
> 🔗 [👉 查看完整 Allure 报告]({report_url})
"""

        payload = {
            'msgtype': 'markdown',
            'markdown': {
                'title': f'{kw_prefix}[{result_status}] {settings.report.title}',
                'text': text,
            },
            'at': {'isAtAll': result_status != 'Success'},
        }
        return payload

    def send_report(self, summary_data: dict[str, Any]) -> None:
        """发送测试结果到钉钉群"""
        if not self.conf.send or not self.conf.webhook:
            return

        log.info('🔔 正在准备发送钉钉机器人通知...')
        payload = self._generate_markdown(summary_data)

        # 动态处理安全策略
        target_url = self.conf.webhook
        if self.conf.secret_type == 'sign' and self.conf.secret:
            target_url = self._get_signed_url()

        try:
            with httpx.Client(timeout=10.0, verify=False) as client:
                headers = {'Content-Type': 'application/json; charset=utf-8', 'Connection': 'close'}
                response = client.post(target_url, json=payload, headers=headers)
                response.raise_for_status()

                res_data = response.json()
                if res_data.get('errcode') == 0:
                    log.info('✅ 钉钉测试报告推送成功！')
                else:
                    log.error(f'❌ 钉钉推送失败，接口返回: {res_data}')

        except Exception as e:
            log.error(f'❌ 钉钉推送执行异常: {e}')


dingding_notifier = DingTalkNotifier()