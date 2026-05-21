from pathlib import Path

from core.parser import parser
from utils.file_manage.file_finder import get_yaml_files

__all__ = ['load_scenarios']


def load_scenarios(folder_path: str | Path):
    """
    用例加载器：供 Pytest 的 @pytest.mark.parametrize 调用
    参考 httpfpt 的 case_data_parse.py 和 ids_extract.py

    :param folder_path: 存放业务场景 YAML 的目录
    :return: (用例对象列表, 用例ID列表)
    """
    yaml_files = get_yaml_files(folder_path)
    scenarios = []
    ids = []

    for file_path in yaml_files:
        # Pydantic 参数格式校验！
        scenario = parser.load_scenario(file_path)
        scenarios.append(scenario)
        # 提取 ID，用于打印 Pytest 控制台日志
        ids.append(f'[{scenario.name}]')

    return scenarios, ids
