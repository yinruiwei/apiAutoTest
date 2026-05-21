import asyncio
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from datetime import datetime
from typing import Any

import pytest

from config.settings import settings
from core.cache_mgr import cache
from core.client import api_client
from core.db_manager import db_mgr
from utils.allure_manage.env_info import resolve_allure_report_url, write_allure_environment_file
from utils.file_manage.path_manager import path_mgr
from utils.reporting_manage.report_notifier import notify_mgr
from utils.logger import log


def _resolve_allure_cli() -> list[str] | None:
    """
    解析 Allure 可执行文件路径。
    PyCharm / GUI 启动的 Python 往往拿不到终端里的 PATH，可设置环境变量 ALLURE_CMD 为绝对路径
    （例如 Allure3 的 allure.bat / allure.cmd）。
    """
    explicit = os.environ.get('ALLURE_CMD', '').strip().strip('"')
    if explicit:
        p = Path(explicit)
        if p.is_file():
            return [str(p.resolve())]
        log.warning(f'ALLURE_CMD 不是有效文件路径，将忽略: {explicit}')

    for name in ('allure', 'allure.cmd', 'allure.bat'):
        found = shutil.which(name)
        if found:
            return [found]

    if sys.platform == 'win32':
        local = Path.home() / 'scoop' / 'shims' / 'allure.cmd'
        if local.is_file():
            return [str(local)]

    return None


def _allure_serve_port() -> str | None:
    """
    allure serve/open 的 --port 参数。
    未设置环境变量时默认 5050，避免每次随机端口；设为 auto/random 则不传 --port（由 Allure 自选）。
    """
    raw = os.environ.get('ALLURE_SERVE_PORT', '5050').strip()
    if raw.lower() in ('auto', 'random'):
        return None
    try:
        n = int(raw)
    except ValueError:
        log.warning(f'ALLURE_SERVE_PORT 无效 [{raw!r}]，改用默认端口 5050')
        return '5050'
    if not (1 <= n <= 65535):
        log.warning(f'ALLURE_SERVE_PORT 超出合法范围 ({n})，改用 5050')
        return '5050'
    return str(n)


def pytest_configure(config: pytest.Config) -> None:
    """记录测试会话开始时间，避免依赖 Pytest 私有属性。"""
    config._rms_session_start_time = time.time()
    n_yaml = path_mgr.clear_report_root_yaml_files()
    log.info(f'运行前已清空 reports 目录下的 YAML 汇总文件: {n_yaml} 个')


# 1. 全局生命周期管理 (Session 级别)
@pytest.fixture(scope='session', autouse=True)
async def session_lifecycle():
    """
    整个测试会话的生命周期管理：
    全部改为原生 async def，享受 pytest-asyncio 的调度，不要用 asyncio.run()
    """
    log.info('🚀 启动测试会话，正在初始化全局基础设施...')
    try:
        await cache.init_check()
        await db_mgr.init_pools()
    except Exception as e:
        log.error(f'基础设施初始化失败，终止测试: {e}')
        pytest.exit(reason=f'基础设施init失败: {e}')

    yield  # 交出控制权，开始执行所有测试用例

    log.info('🏁 测试会话结束，正在清理并释放资源...')
    await api_client.close()  # 释放 HTTPX 资源
    await db_mgr.close_pools()


# 2. 用例级生命周期管理 (Function 级别)
@pytest.fixture(autouse=True)
def function_logger(request: pytest.FixtureRequest):
    """
    自动在日志中清晰地划分每个用例的边界
    """
    # 尝试获取用例的中文描述 (docstring)
    desc = request.function.__doc__ or request.node.name
    log.info('')
    log.info(f'▶️ 开始执行用例: {desc}')

    yield

    log.info(f'⏹️ 用例执行完毕: {desc}\n')


# 3. Pytest 核心钩子 (Hooks)
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """
    修复 Pytest 收集用例时，控制台输出的中文名出现 Unicode 乱码的问题
    """
    for item in items:
        item.name = item.name.encode('utf-8').decode('unicode_escape')
        item._nodeid = item.nodeid.encode('utf-8').decode('unicode_escape')


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item: pytest.Item, call: Any):
    """
    获取测试结果，将用例的 docstring 注入到报告的 description 中
    以便后续 Allure 报告能够展示清晰的中文用例说明
    """
    outcome = yield
    report = outcome.get_result()
    if getattr(item.function, '__doc__', None):
        report.description = str(item.function.__doc__).strip()


def pytest_terminal_summary(terminalreporter: Any, exitstatus: int, config: pytest.Config) -> None:
    """
    测试结束后的终局统计，生成简易的 YAML 结果摘要
    """
    started_time = getattr(config, '_rms_session_start_time', time.time())
    elapsed_seconds = float(time.time() - started_time)
    hours, remainder = divmod(elapsed_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    stats = terminalreporter.stats
    passed = len(stats.get('passed', []))
    failed = len(stats.get('failed', []))
    error = len(stats.get('error', []))
    skipped = len(stats.get('skipped', []))
    total = terminalreporter._numcollected

    env_props = write_allure_environment_file()
    allure_url = resolve_allure_report_url()

    # 组装摘要数据
    summary_data = {
        'project': settings.project_name,
        'result': 'Success' if (failed == 0 and error == 0) else 'Failed',
        'total': total,
        'passed': passed,
        'failed': failed,
        'error': error,
        'skipped': skipped,
        'started_time': datetime.fromtimestamp(started_time).strftime('%Y-%m-%d %H:%M:%S'),
        'elapsed_time': f'{int(hours):02}:{int(minutes):02}:{int(seconds):02}',
        'run_env': env_props.get('RUN_ENV', os.environ.get('RUN_ENV', 'dev')),
        'runner_host': env_props.get('Runner.Host', ''),
        'allure_report_url': allure_url,
        'target_hosts': {k: v for k, v in env_props.items() if k.startswith('Target.')},
    }

    # 写入报告目录
    report_file = path_mgr.report_dir / f'summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.yaml'
    try:
        from utils.file_manage.yaml_handler import write_yaml
        write_yaml(report_file, summary_data)
        log.info(f"📊 测试结果摘要已生成: {report_file.name}")

        notify_mgr.send_all_notifications(summary_data, report_file)

    except Exception as e:
        log.error(f'生成或发送测试摘要失败: {e}')


def pytest_unconfigure(config: pytest.Config) -> None:
    """
    进程退出前的最后阶段（晚于 pytest_terminal_summary）。
    在此处阻塞执行 allure serve，避免抢先占用进程导致摘要 YAML / 钉钉邮件等通知无法发送。
    """
    if os.environ.get('PYTEST_XDIST_WORKER'):
        return
    flag = os.environ.get('AUTO_ALLURE_SERVE', '').strip().lower()
    if flag not in ('1', 'true', 'yes', 'on'):
        return
    port = _allure_serve_port()
    port_hint = f'端口 {port}' if port else '端口由 Allure 随机分配（ALLURE_SERVE_PORT=auto）'
    report_url = resolve_allure_report_url()
    log.info(f'📊 AUTO_ALLURE_SERVE：正在执行 allure serve（{port_hint}，关闭：Ctrl+C）…')
    log.info(f'📊 报告访问地址（本机局域网）: {report_url}')
    cli = _resolve_allure_cli()
    if not cli:
        log.error(
            '❌ 未找到 allure 可执行文件。PyCharm 运行时的 PATH 常与 CMD 不一致（与 Allure2/3 无关）。\n'
            '   处理方式任选其一：\n'
            '   1) 在运行配置「环境变量」中设置 ALLURE_CMD=你的 allure.bat 绝对路径；\n'
            '   2) 在同一运行配置里把「Path」改为继承系统 PATH，或追加 Allure 的 bin 目录。'
        )
        return
    log.debug(f'使用 Allure CLI: {cli[0]}')
    try:
        if port:
            serve_cmd = [*cli, 'serve', '-h', '0.0.0.0', '--port', port, str(path_mgr.allure_results_dir)]
        else:
            serve_cmd = [*cli, 'serve', '-h', '0.0.0.0', str(path_mgr.allure_results_dir)]

        subprocess.run(serve_cmd, check=False)
    except OSError as e:
        log.error(f'❌ 无法启动 allure serve: {e}')


@pytest.fixture(scope='session', autouse=True)
async def global_wms_login(session_lifecycle):
    # 注意：把 session_lifecycle 传进来，保证它在基础设施连通后再执行登录
    """全局自动登录，拿 Token 放进 Redis 缓存池"""
    log.info('🔥 执行全局前置：WMS 登录')

    acc = settings.wms_login_test_account
    if acc.username and acc.password:
        # 与 api/wms/login.yaml 一致使用 /user/login，避免误打到其它网关路径
        res = await api_client.send_request(
            rendered_request={
                'method': 'POST',
                'url': '/user/login',
                'headers': {'Content-Type': 'application/json'},
                'json': {'userName': acc.username, 'password': acc.password},
            },
            base_url=settings.base_urls.wms,
        )
        log.debug(f'全局 WMS 登录响应: HTTP {res.status_code} | {res.text[:300]}')
    else:
        log.warning('未配置 wms_login_test_account.username/password，跳过全局 WMS 登录')

    yield

@pytest.fixture(scope='session', autouse=True)
async def global_rms_login(session_lifecycle):
    log.info('🔥 执行全局前置：RMS 登录')

    acc = settings.rms_login_test_account
    if acc.username and acc.password:
        # 与 api/rms/login.yaml 一致使用 /user/login，避免误打到其它网关路径
        res = await api_client.send_request(
            rendered_request={
                'method': 'POST',
                'url': '/user/login',
                'headers': {'Content-Type': 'application/json'},
                'json': {'userName': acc.username, 'password': acc.password},
            },
            base_url=settings.base_urls.rms,
        )
        log.debug(f'全局 RMS 登录响应: HTTP {res.status_code} | {res.text[:300]}')
    else:
        log.warning('未配置 rms_login_test_account.username/password，跳过全局 RMS 登录')

    yield