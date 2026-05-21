from functools import cache
from pathlib import Path

__all__ = ['path_mgr']


class ProjectPathConfig:
    """全局路径管理配置"""

    def __init__(self) -> None:
        # 获取当前文件 (path_manager.py) 的绝对路径,并向上推三级到达项目根目录
        self.project_dir: Path = Path(__file__).resolve().parents[2]

        # 静态代码与配置目录
        self.api_dir: Path = self.project_dir / 'api'
        self.testcases_dir: Path = self.project_dir / 'testcases'
        self.extensions_dir: Path = self.project_dir / 'extensions'
        self.core_dir: Path = self.project_dir / 'core'
        self.config_dir: Path = self.project_dir / 'config'
        self.data_dir: Path = self.project_dir / 'data'
        self.utils_dir: Path = self.project_dir / 'utils'
        self.docs_dir: Path = self.project_dir / 'doc'

        # 动态产物目录 (日志、报告)
        self.log_dir: Path = self.project_dir / 'logs'
        self.report_dir: Path = self.project_dir / 'reports'
        self.allure_results_dir: Path = self.report_dir / 'allure_results'
        self.html_report_dir: Path = self.report_dir / 'html_report'

        # 特殊文件路径
        self.env_file: Path = self.project_dir / '.env'
        self.debugtalk_file: Path = self.project_dir / 'debugtalk.py'

        # 初始化时自动创建动态目录
        self._ensure_dynamic_dirs_exist()

    def _ensure_dynamic_dirs_exist(self) -> None:
        """
        确保动态生成的目录存在。
        parents=True: 如果父目录不存在则一并创建。
        exist_ok=True: 如果目录已存在则不会抛出 FileExistsError 异常。
        """
        dir_list = [
            self.log_dir,
            self.report_dir,
            self.allure_results_dir,
            self.html_report_dir,
        ]
        for d in dir_list:
            d.mkdir(parents=True, exist_ok=True)

    def clear_report_root_yaml_files(self) -> int:
        """
        删除 reports 目录顶层生成的 *.yaml（如 summary_*.yaml）。
        不递归子目录，避免误删 Allure 等工具产生的其它文件。
        """
        if not self.report_dir.is_dir():
            return 0
        removed = 0
        for p in self.report_dir.glob('*.yaml'):
            try:
                p.unlink()
                removed += 1
            except OSError:
                continue
        return removed


@cache
def get_path_config() -> ProjectPathConfig:
    """使用 lru_cache 确保全局只实例化一次,提升性能"""
    return ProjectPathConfig()


# 全局单例
path_mgr = get_path_config()
