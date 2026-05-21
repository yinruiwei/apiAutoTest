import datetime
import operator
from os import getenv

from faker import Faker

from config.settings import LoginTestAccount, settings

faker = Faker(locale='zh_CN')


def current_time() -> datetime.datetime:
    """
    :return: 获取当前时间
    """
    return datetime.datetime.now()


def random_phone() -> str:
    """
    :return: 随机手机号
    """
    return faker.phone_number()

def random_name() -> str:
    """
    :return: 随机名称
    """
    return faker.name()


def gen_order_no(prefix: str = 'AUTO') -> str:
    """生成可读的唯一订单号（供 YAML 场景引用）。"""
    return f'{prefix}_{datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")}'


def get_env(name: str, default: str = '') -> str:
    """读取进程环境变量。"""
    return getenv(name, default)


def _require_login_field(acc: LoginTestAccount, section: str, field: str) -> str:
    val = acc.username if field == 'username' else acc.password
    if not val:
        raise ValueError(f'未配置 {section}.{field}，请在 config/env.{{RUN_ENV}}.yaml 中填写')
    return val


def wms_login_username() -> str:
    """WMS 登录场景专用用户名（对应配置块 wms_login_test_account）。"""
    return _require_login_field(settings.wms_login_test_account, 'wms_login_test_account', 'username')


def wms_login_password() -> str:
    """WMS 登录场景专用密码。"""
    return _require_login_field(settings.wms_login_test_account, 'wms_login_test_account', 'password')


def rms_login_username() -> str:
    """RMS 登录场景专用用户名（对应配置块 rms_login_test_account）。"""
    return _require_login_field(settings.rms_login_test_account, 'rms_login_test_account', 'username')


def rms_login_password() -> str:
    """RMS 登录场景专用密码。"""
    return _require_login_field(settings.rms_login_test_account, 'rms_login_test_account', 'password')
