import argparse
import os
import sys

import pytest

from utils.allure_manage.env_info import resolve_allure_report_url
from utils.file_manage.path_manager import path_mgr
from utils.logger import log


def show_banner():
    """打印项目启动 Banner"""


def run():
    """
    运行入口
    负责解析命令行参数，设置环境变量，并驱动 Pytest 和 Allure
    """
    parser = argparse.ArgumentParser(description='RMS API Test Framework 启动引擎')

    # 定义命令行参数
    parser.add_argument('-e', '--env', default='dev', choices=['dev', 'test', 'prod'], help='运行环境 (默认: dev)')
    parser.add_argument('-m', '--mark', default='', help='运行指定标签的用例 (例如: p0, wms, rms)')
    parser.add_argument(
        '-S',
        '--serve',
        action='store_true',
        help='测试结束后执行 allure serve，自动打开浏览器查看报告；在终端按 Ctrl+C 停止服务后本进程退出',
    )
    parser.add_argument(
        '--allure-port',
        default=os.environ.get('ALLURE_SERVE_PORT', '5050'),
        metavar='PORT',
        help='与 -S 配合：allure serve/open 固定监听端口（默认 5050；设为 auto 则仍由 Allure 随机选端口）',
    )
    parser.add_argument('-w', '--workers', default='0', help='并发执行的进程数 (如填 4，需安装 pytest-xdist)')

    args = parser.parse_args()

    # 1. 注入环境变量，让 config/settings.py 能够动态加载对应的 env.xxx.yaml
    os.environ['RUN_ENV'] = args.env
    if args.serve:
        # 由 conftest pytest_unconfigure 统一拉起 allure serve（晚于终端摘要与通知）
        os.environ['AUTO_ALLURE_SERVE'] = '1'
        os.environ['ALLURE_SERVE_PORT'] = str(args.allure_port).strip()
        log.info(f'📊 Allure 报告地址: {resolve_allure_report_url()}')

    show_banner()
    log.info(f'🔥 启动配置 -> 环境: [{args.env.upper()}] | 标签: [{args.mark or "全量"}] | 并发数: [{args.workers}]')

    # 2. 组装 Pytest 运行参数
    pytest_args = [
        '-v',
        '-s',
        f'--alluredir={path_mgr.allure_results_dir}',
        '--clean-alluredir',  # 每次运行前清空旧报告数据
    ]

    # 追加自定义标签
    if args.mark:
        pytest_args.extend(['-m', args.mark])

    # 追加并发参数
    # TODO: 并发参数后续提取配置文件
    if args.workers != '0':
        pytest_args.extend(['-n', args.workers])

    # 3. 把控制权交给 Pytest
    log.info(f'⚙️  底层执行命令: pytest {" ".join(pytest_args)}')
    exit_code = pytest.main(pytest_args)

    # 退出脚本并返回 Pytest 的状态码
    sys.exit(exit_code)


if __name__ == '__main__':
    run()
