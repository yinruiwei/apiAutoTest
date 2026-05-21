import json

from typing import Any

import allure

from allure_commons.types import AttachmentType


class AllureManager:
    """Allure 报告扩展管理器"""

    @staticmethod
    def step(name: str):
        """
        用法: with allure_mgr.step("步骤1: 登录"): ...
        """
        return allure.step(name)

    @staticmethod
    def attach_json(name: str, data: dict | list | str | bytes | None):
        """
        向 Allure 报告中附加美化后的 JSON 数据
        """
        if not data:
            return

        try:
            if isinstance(data, (dict, list)):
                content = json.dumps(data, ensure_ascii=False, indent=2)
            elif isinstance(data, (str, bytes)):
                # 尝试将字符串/字节解析为 dict 再美化
                content = json.dumps(json.loads(data), ensure_ascii=False, indent=2)
            else:
                content = str(data)
        except Exception:
            content = str(data)

        allure.attach(body=content, name=name, attachment_type=AttachmentType.JSON)

    @staticmethod
    def attach_text(name: str, content: Any):
        """
        向 Allure 报告中附加纯文本数据
        """
        if not content:
            return

        allure.attach(body=str(content), name=name, attachment_type=AttachmentType.TEXT)


# 暴露单例
allure_mgr = AllureManager()
