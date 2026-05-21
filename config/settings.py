import os

import yaml

from pydantic import BaseModel

from core.exceptions import EnvConfigError
from utils.file_manage.path_manager import path_mgr


class BaseUrlsConfig(BaseModel):
    # 与 api/ 文件夹下的子文件夹对应
    wms: str
    rms: str
    pda: str
    hub: str = ''


class ReportConfig(BaseModel):
    title: str = '自动化测试报告'
    tester_name: str = 'QA'
    allure_port: int = 5050
    # 已废弃固定报告地址：通知与 Allure 环境信息改由 utils.allure_manage.env_info 按本机 IP + 端口自动生成。
    # 若需强制指定报告 URL，请设置环境变量 ALLURE_REPORT_URL。
    jenkins_url: str = ''


class DBConfig(BaseModel):
    host: str
    port: int
    user: str
    db_name: str
    password: str = ''


class RedisConfig(BaseModel):
    host: str
    port: int
    db: int = 0
    timeout: int = 10
    password: str = ''


class EmailConfig(BaseModel):
    host: str
    port: int
    user: str
    password: str = ''
    receiver: str | list[str]  # 支持单发或群发
    ssl: bool = True
    send: bool = False  # 发送总开关


class DingTalkConfig(BaseModel):
    webhook: str = ''
    secret_type: str = 'keywords'  # 'keywords' (关键字) 或 'sign' (加签)
    secret: str = ''  # 关键字内容 或 加签的密钥
    send: bool = False  # 钉钉发送总开关


class NotifyConfig(BaseModel):
    feishu_webhook: str = ''
    dingding: DingTalkConfig = DingTalkConfig()


class LoginTestAccount(BaseModel):
    """单系统登录场景用账号；密码按该环境接口约定填写（明文 / MD5 等），勿在模型层写默认真实账号。"""

    username: str = ''
    password: str = ''


class Settings(BaseModel):
    project_name: str
    base_urls: BaseUrlsConfig
    databases: dict[str, DBConfig]
    redis: RedisConfig
    notify: NotifyConfig
    email: EmailConfig
    report: ReportConfig
    wms_login_test_account: LoginTestAccount = LoginTestAccount()
    rms_login_test_account: LoginTestAccount = LoginTestAccount()


def load_settings() -> Settings:
    """
    加载全局配置
    只需在运行终端设置环境变量，如： set RUN_ENV=test (Windows) 或 export RUN_ENV=test (Linux/Mac)
    如果不设置，默认加载 env.dev.yaml
    """
    env_name = os.getenv('RUN_ENV', 'dev')
    yaml_path = path_mgr.config_dir / f'env.{env_name}.yaml'

    if not yaml_path.exists():
        raise EnvConfigError(f'环境配置文件不存在: {yaml_path}')

    with open(yaml_path, encoding='utf-8') as f:
        yaml_data = yaml.safe_load(f)

    # 将 YAML 字典直接交给 Pydantic 进行类型校验并实例化
    return Settings(**yaml_data)


# 全局唯一的配置对象
settings = load_settings()
