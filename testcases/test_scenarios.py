import importlib.util
from typing import Any

import allure
import pytest
from allure_commons.types import LabelType

from core.models import ScenarioModel
from core.scenario.scenario_runner import ScenarioRunner
from core.scenario.yaml_scenario_loader import load_scenarios
from utils.file_manage.path_manager import path_mgr

SCENARIOS, _SCENARIO_IDS = load_scenarios(path_mgr.testcases_dir / 'scenarios')

# 同一场景多步共用一个 Runner（上下文变量串联）。key = scenario_index
_flow_runners: dict[int, ScenarioRunner] = {}


def _marks_for_flow_step(scenario: ScenarioModel, scenario_index: int, step_index: int) -> list[Any]:
    """
    Epic / Feature / Story 通过 pytest 的 allure_label 写入（在 teardown 时由 allure-pytest 收集），
    """
    step = scenario.teststeps[step_index]
    conf: dict[str, Any] = (scenario.config or {}).get('allure') or {}
    marks: list[Any] = []

    epic = conf.get('epic')
    if epic is not None and str(epic).strip():
        marks.append(pytest.mark.allure_label(str(epic).strip(), label_type=LabelType.EPIC))

    feature = conf.get('feature')
    if feature is not None and str(feature).strip():
        marks.append(pytest.mark.allure_label(str(feature).strip(), label_type=LabelType.FEATURE))

    marks.append(pytest.mark.allure_label(step.name, label_type=LabelType.STORY))

    if importlib.util.find_spec('xdist') is not None:
        xdist_group = getattr(pytest.mark, 'xdist_group', None)
        if xdist_group is not None:
            marks.append(xdist_group(f'yaml-flow-{scenario_index}'))

    return marks


def _build_flow_step_params() -> tuple[list[Any], list[str]]:
    """每个 YAML 步骤 → 一条 Pytest 用例，Epic/Feature/Story 通过 allure_label 标记写入。"""
    cases: list[Any] = []
    ids: list[str] = []
    for si, scenario in enumerate(SCENARIOS):
        for ti in range(len(scenario.teststeps)):
            step = scenario.teststeps[ti]
            marks = _marks_for_flow_step(scenario, si, ti)
            cases.append(pytest.param(si, ti, marks=marks))
            ids.append(f'[{scenario.name}]#{ti + 1}-{step.name}')
    return cases, ids


_FLOW_STEP_CASES, _FLOW_STEP_IDS = _build_flow_step_params()


def _apply_allure_labels(scenario: ScenarioModel, step_index: int) -> None:
    step = scenario.teststeps[step_index]
    # Epic/Feature/Story 已在 pytest.param 的 marks 中；此处只设标题与参数
    allure.dynamic.title(step.name)
    allure.dynamic.parameter('场景名称', scenario.name)
    allure.dynamic.parameter('步骤名称', step.name)
    allure.dynamic.parameter('步骤序号', step_index + 1)


@pytest.mark.parametrize('scenario_index,step_index', _FLOW_STEP_CASES, ids=_FLOW_STEP_IDS)
async def test_yaml_scenario(scenario_index: int, step_index: int):
    """每个 YAML 步骤单独一条用例；Epic/Feature/Story 见收集阶段 allure_label marks。"""

    scenario = SCENARIOS[scenario_index]
    _apply_allure_labels(scenario, step_index)

    if step_index == 0:
        runner = ScenarioRunner()
        runner.apply_scenario_config_variables(scenario)
        _flow_runners[scenario_index] = runner
    else:
        runner = _flow_runners.get(scenario_index)
        if runner is None:
            pytest.fail(
                f'场景 [{scenario.name}] 缺少前置步骤上下文（step_index={step_index}）。'
                '请勿单独筛选中间步骤执行；同一场景须从第 1 步顺序跑，或勿使用 pytest-xdist 拆散同一场景各步。'
            )

    await runner.run_single_step(scenario, step_index)

    if step_index == len(scenario.teststeps) - 1:
        _flow_runners.pop(scenario_index, None)
