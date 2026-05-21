"""Allure 环境信息：自动解析执行机 IP 与被测服务地址，不依赖 report.jenkins_url 固定配置。"""

from __future__ import annotations

import os
import socket
from urllib.parse import urlparse

from config.settings import BaseUrlsConfig, settings
from utils.file_manage.path_manager import path_mgr
from utils.logger import log

__all__ = [
    'build_allure_environment_properties',
    'resolve_allure_report_url',
    'write_allure_environment_file',
]


def get_local_lan_ip() -> str:
    """获取本机局域网 IP（用于 allure serve 报告链接，非 127.0.0.1）。"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(('8.8.8.8', 80))
            return sock.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return '127.0.0.1'


def _hosts_from_base_urls(base_urls: BaseUrlsConfig) -> dict[str, str]:
    """从 base_urls 解析各系统 hostname（多为被测环境 IP 或域名）。"""
    hosts: dict[str, str] = {}
    for key in ('wms', 'rms', 'pda', 'hub'):
        raw = getattr(base_urls, key, '') or ''
        if not isinstance(raw, str) or not raw.strip():
            continue
        parsed = urlparse(raw.strip())
        host = parsed.hostname
        if host:
            hosts[key] = host
    return hosts


def _resolve_serve_port() -> int:
    raw = os.environ.get('ALLURE_SERVE_PORT', '').strip()
    if raw.lower() in ('auto', 'random', ''):
        return int(settings.report.allure_port)
    try:
        port = int(raw)
    except ValueError:
        return int(settings.report.allure_port)
    return port if 1 <= port <= 65535 else int(settings.report.allure_port)


def resolve_allure_report_url() -> str:
    """
    生成 Allure 报告访问地址。
    优先级：环境变量 ALLURE_REPORT_URL > 本机 IP + 端口（ALLURE_SERVE_PORT / settings.report.allure_port）。
    """
    explicit = os.environ.get('ALLURE_REPORT_URL', '').strip()
    if explicit:
        return explicit.rstrip('/') + '/'

    host = get_local_lan_ip()
    port = _resolve_serve_port()
    return f'http://{host}:{port}/'


def build_allure_environment_properties() -> dict[str, str]:
    """组装写入 Allure environment.properties 的键值。"""
    run_env = os.environ.get('RUN_ENV', 'dev')
    runner_ip = get_local_lan_ip()
    target_hosts = _hosts_from_base_urls(settings.base_urls)
    serve_port = str(_resolve_serve_port())

    props: dict[str, str] = {
        'RUN_ENV': run_env,
        'Project': settings.project_name,
        'Runner.Host': runner_ip,
        'Allure.Serve.Host': runner_ip,
        'Allure.Serve.Port': serve_port,
        'Allure.Report.URL': resolve_allure_report_url(),
    }
    for system, host in target_hosts.items():
        props[f'Target.{system.upper()}'] = host

    return props


def write_allure_environment_file(results_dir=None) -> dict[str, str]:
    """写入 reports/allure_results/environment.properties，供 Allure 报告「环境」区块展示。"""
    out_dir = results_dir or path_mgr.allure_results_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    props = build_allure_environment_properties()
    lines = [f'{k}={v}' for k, v in props.items()]
    env_file = out_dir / 'environment.properties'
    env_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    log.info(f'📎 已写入 Allure 环境文件: {env_file.name}（Runner={props.get("Runner.Host")}）')
    return props
