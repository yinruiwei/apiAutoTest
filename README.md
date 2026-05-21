# 智能仓储自动化测试系统 (RMS API Test Framework)

面向 **WMS / RMS / PDA** 等子系统的 **HTTP 接口自动化测试框架**。采用 **API 积木（YAML）+ 业务场景（YAML）** 分层设计，配合 **Pytest + httpx 异步** 执行，**Allure** 生成可交互报告，支持钉钉/邮件等通知扩展。

---

## 1. 功能介绍

| 能力 | 说明 |
|------|------|
| **API 对象模式** | 在 `api/` 下按系统（`wms` / `rms` / `pda`）维护接口契约；场景只引用路径，避免重复维护 URL、Method、默认 Header。 |
| **场景编排** | 在 `testcases/scenarios/` 用 YAML 描述多步骤流程，步骤间通过 **变量提取 / 上下文传递** 串联（如先登录拿 Token，再调业务接口）。 |
| **异步 HTTP** | 基于 `httpx.AsyncClient`，会话级连接池，适合接口回归与批量场景。 |
| **断言中心** | 支持等值、大小比较、包含、长度、正则、JSON Schema 等断言；**先校验再提取**，避免失败响应误抽 Token。 |
| **动态数据** | YAML 中通过 `$变量` 与 `${hook函数()}` 注入请求参数；Hook 在受限沙箱内执行，禁止任意系统调用。 |
| **环境隔离** | `config/env.{dev,test,prod}.yaml` + 环境变量 `RUN_ENV` 切换 Base URL、数据库、Redis、通知与登录测试账号。 |
| **测试报告** | 默认输出 Allure 原始结果到 `reports/allure_results`；`run.py -S` 可在会话结束后自动 `allure serve`。 |
| **可观测性** | Loguru 文件/控制台日志；Allure 步骤内附加请求/响应 JSON（鉴权头脱敏）。 |
| **扩展工具** | Postman Collection 可导入为 `api/*.yaml` 草稿（`utils/data_manage/postman.py`）。 |

**典型工作流**：编写/引用 API 积木 → 编写场景 YAML → `python run.py -e dev` → 查看 Allure / 日志 / 通知。

---

## 2. 目录结构

```text
rms_api_test/
├── run.py                      # 命令行入口：环境、标签、Allure serve、并发
├── conftest.py                 # Pytest 会话 fixture、摘要通知、Allure serve 收尾
├── debugtalk.py                # 对外导出 Hook（可选，与 extensions 白名单配合）
├── pytest.ini                  # Pytest / asyncio / markers / 默认 alluredir
├── pyproject.toml              # 依赖与 Python 版本（推荐 uv）
├── uv.lock                     # 锁定依赖版本
├── requirements.txt            # 导出的依赖清单（CI / pip 兼容）
│
├── api/                        # 【接口契约层】API 积木 YAML
│   ├── wms/                    # WMS 接口（如 login.yaml、order_api.yaml）
│   ├── rms/                    # RMS 接口（如 login.yaml、warehouse_manage/…）
│   └── pda/                    # PDA 接口（如 pick_api.yaml）
│
├── testcases/
│   ├── test_scenarios.py       # Pytest 收集 scenarios 下 YAML，驱动 ScenarioRunner
│   ├── template_api.yaml       # 新建 API 积木模板
│   ├── template_flow.yaml      # 新建场景流模板
│   └── scenarios/              # 业务场景（可按 RMS/WMS 分子目录）
│       ├── RMS/登录/test_rms_login.yaml
│       ├── RMS/仓库管理/test_rms_warehouse.yaml
│       └── WMS/登录/test_wms_login.yaml
│
├── core/                       # 【引擎】解析、HTTP、断言、场景状态机
│   ├── models.py               # Pydantic 模型（与 YAML 字段对应）
│   ├── parser.py               # 加载 YAML、Hook + 变量渲染
│   ├── client.py               # httpx 异步客户端
│   ├── asserter.py             # 断言分发
│   ├── cache_mgr.py            # 本地 / Redis 缓存
│   ├── db_manager.py           # aiomysql 连接池（预留）
│   └── scenario/
│       ├── scenario_runner.py  # setup → 请求 → validate → extract
│       └── yaml_scenario_loader.py
│
├── config/
│   ├── settings.py             # 读取 env.{RUN_ENV}.yaml
│   ├── env.dev.yaml            # 开发环境示例
│   └── env.test.yaml           # 测试环境示例
│
├── enums/                      # 断言类型、HTTP 方法、Setup/Teardown 等枚举
├── extensions/                 # YAML 可调用的 Hook 函数实现
│   ├── common_funcs.py
│   ├── wms_funcs.py
│   ├── rms_funcs.py
│   └── pda_funcs.py
│
├── utils/
│   ├── file_manage/            # 路径、YAML 读写、用例发现
│   ├── parsing_manage/         # Hook 执行、变量替换、JSONPath
│   ├── reporting_manage/       # Allure 封装、钉钉/邮件通知
│   ├── allure_manage/
│   ├── data_manage/            # Postman 导入等
│   └── logger.py
│
├── data/                       # CSV 等外部静态数据（数据驱动预留）
├── logs/                       # 运行日志（建议 .gitignore）
└── reports/                    # Allure 结果与 HTML（建议 .gitignore）
    ├── allure_results/
    └── html_report/
```

---

## 3. 项目本地开发配置步骤

### 3.1 环境要求

- **Python ≥ 3.12**
- 推荐包管理：**[uv](https://github.com/astral-sh/uv)**（项目已配置清华 PyPI 镜像）
- 查看 Allure 报告需安装 **Allure Commandline**（2.x/3.x 均可），并保证 `allure` 在 PATH 中；若 IDE 找不到命令，可设置环境变量 `ALLURE_CMD` 为 `allure.bat` / `allure.cmd` 的绝对路径。

### 3.2 克隆与安装依赖

```bash
git clone https://gitee.com/yin-ruiwei/rms_api_test.git
cd rms_api_test

# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -r requirements.txt
```

开发依赖（含 `pytest`、`pytest-asyncio`、`ruff`、`pre-commit`）：

```bash
uv sync --group dev
```

### 3.3 配置运行环境

1. 复制或编辑 `config/env.dev.yaml`（测试环境用 `env.test.yaml`）。
2. 重点配置项：
   - **`base_urls`**：`wms` / `rms` / `pda` 的完整根地址（场景里 API 路径为相对路径，如 `/user/login`）。
   - **`wms_login_test_account` / `rms_login_test_account`**：登录场景专用账号，两套互相独立。
   - **`databases` / `redis` / `notify` / `email`**：按需启用（通知默认可在 YAML 里 `send: false` 关闭）。

3. 通过环境变量切换配置（`run.py` 会自动设置）：

   | 变量 | 含义 |
   |------|------|
   | `RUN_ENV` | `dev` / `test` / `prod`，对应加载 `config/env.{RUN_ENV}.yaml` |
   | `AUTO_ALLURE_SERVE` | 设为 `1` 时，测试结束后在 `pytest_unconfigure` 阶段执行 `allure serve` |
   | `ALLURE_SERVE_PORT` | 与 `-S` 配合，默认 `5050`；`auto` 表示由 Allure 随机端口 |
   | `ALLURE_CMD` | Allure 可执行文件绝对路径（可选） |

### 3.4 运行测试

```bash
# 默认 dev 环境，全量场景
python run.py

# 指定 test 环境
python run.py -e test

# 按 Pytest 标记筛选（见 pytest.ini markers）
python run.py -m rms

# 结束后自动打开 Allure（Ctrl+C 结束 serve 后进程退出）
python run.py -S

# 直接使用 pytest（与 run.py 等价的核心参数已在 pytest.ini）
uv run pytest testcases/test_scenarios.py -m wms
```

### 3.5 代码质量（可选）

```bash
# 安装 pre-commit 钩子
uv run pre-commit install

# 手动格式化 / 检查
uv run ruff check .
uv run ruff format .
```

### 3.6 新增用例的快速路径

1. 在 `api/{系统}/` 新建或维护接口 YAML（可参考 `testcases/template_api.yaml`）。
2. 在 `testcases/scenarios/` 新建场景 YAML（可参考 `testcases/template_flow.yaml` 或现有登录/仓库用例）。
3. 执行 `python run.py -m <标签>` 验证；在 `reports/allure_results` 或 `-S` 查看报告。

---

## 4. 用例 YAML 格式说明

框架有两类 YAML：**API 积木**（`api/`）与 **业务场景**（`testcases/scenarios/`）。字段由 `core/models.py` 的 Pydantic 模型校验，多余字段会报错（`extra='forbid'`）。

### 4.1 API 积木（`api/**/*.yaml`）

对应模型：`ApiDefinitionModel`。

```yaml
name: "RMS系统-登录接口"

request:
  method: "POST"              # 枚举：GET / POST / PUT / DELETE 等（见 enums/request/method.py）
  url: "/user/login"          # 相对路径；完整 URL 由 api 路径前缀解析 base_urls（api/rms/ → rms）
  headers:
    Content-Type: "application/json"
  json:                       # 请求体；YAML 关键字 json 映射为模型 json_data
    userName: "$username"     # $变量 由场景 steps.variables 或 config.variables 注入
    password: "$password"

# 可选：接口级默认断言（场景步骤可追加 validate）
validate:
  - assert_type: "eq"
    jsonpath: "$.code"
    expect_value: 200
    message: "可选的自定义失败说明"
```

**约定**

- API 文件路径建议为 `api/{wms|rms|pda}/...`，以便自动选择 `config` 里对应 `base_urls`。
- 登录等「同一接口、正反场景并存」的接口，**不建议在 API 层写 extract**；失败时 `data` 常为 `null`，统一提取易触发 JSONPath 错误。提取与业务断言放在场景步骤中按需编写。

### 4.2 业务场景（`testcases/scenarios/**/*.yaml`）

对应模型：`ScenarioModel` → `teststeps[]` → `StepModel`。

```yaml
name: "RMS登录模块"

config:
  module: "RMS_AUTH"          # 自定义元数据，便于分类
  allure:
    epic: "RMS"
    feature: "登录模块"
  variables:                  # 场景级全局变量，每个场景开始前注入上下文
    global_flag: true

teststeps:
  - name: "用例1：错误密码"
    api: "api/rms/login.yaml"   # 相对项目根目录
    variables:
      username: '${rms_login_username()}'
      password: "wrong"
    validate:
      - assert_type: "eq"
        jsonpath: "$.code"
        expect_value: 6302
      - assert_type: "contains"
        jsonpath: "$.message"
        expect_value: "用户名或密码错误"

  - name: "用例2：登录成功并提取 Token"
    api: "api/rms/login.yaml"
    variables:
      username: '${rms_login_username()}'
      password: '${rms_login_password()}'
    validate:                   # 先执行 validate，再 extract（避免失败响应误提取）
      - assert_type: "eq"
        jsonpath: "$.code"
        expect_value: 200
    extract:
      - var_name: "rms_token"
        jsonpath: "$.data"
```

**单步执行顺序**

1. 合并 `config.variables` 与当前步 `variables`（经 Hook → `$变量` 渲染）
2. 加载 API 积木并渲染请求
3. 发送 HTTP 请求
4. 合并 API 与步骤的 **`validate`** 并断言
5. 合并 API 与步骤的 **`extract`**，写入场景上下文，供后续步骤使用 `$变量名`

**变量写法**

| 写法 | 说明 | 示例 |
|------|------|------|
| `$var_name` | 引用上下文变量；整段为 `$name` 时保留类型，内联时转为字符串 | `Authorization: Bearer $rms_token` |
| `${func()}` | 调用 extensions 白名单内的 Python 函数 | `'${rms_login_username()}'` |
| `${func(arg)}` | 支持位置参数；内联时结果 `str()` 拼接 | `order_sn: "PRE_${gen_order_no()}"` |

渲染顺序：**先 Hook（`${}`），再 `$变量` 替换**（见 `core/parser.py`）。

### 4.3 断言类型（`assert_type`）

YAML 中 `assert_type` 填写 **字符串枚举值**（定义于 `enums/assert_type.py`，由 Pydantic 校验）。`jsonpath` 从**响应 JSON** 取值；`expect_value` 支持字面量，也可在断言前经变量渲染。

| YAML 值 | 含义 | 说明 |
|---------|------|------|
| `eq` | 相等 | `actual == expect` |
| `not_eq` | 不等 | `actual != expect` |
| `gt` / `ge` / `lt` / `le` | 数值比较 | 需双方可比较 |
| `str_eq` | 字符串相等 | `str(actual) == str(expect)` |
| `len_eq` | 长度等于 | `len(actual) == int(expect)` |
| `not_len_eq` | 长度不等于 | 枚举已定义；**asserter 待实现** |
| `len_lt` / `len_le` / `len_gt` / `len_ge` | 长度比较 | `len_lt`/`len_gt`/`len_eq` 已实现；`len_le`/`len_ge`/`not_len_eq` 枚举有、引擎待补齐 |
| `contains` | 包含 | `expect in actual`（子串或元素） |
| `not_contains` | 不包含 | `expect not in actual` |
| `startswith` | 前缀 | 转字符串后比较 |
| `endswith` | 后缀 | 转字符串后比较 |
| `regex` | 正则 | `re.search(expect, str(actual))` |
| `jsonschema` | JSON Schema | `expect_value` 为 Schema 字典；`jsonpath` 常为 `"$"` 表示整段响应 |

**示例**

```yaml
validate:
  - assert_type: "eq"
    jsonpath: "$.code"
    expect_value: 200
  - assert_type: "regex"
    jsonpath: "$.data.orderNo"
    expect_value: "^AUTO_\\d+$"
  - assert_type: "jsonschema"
    jsonpath: "$"
    expect_value:
      type: object
      required: [code, message]
      properties:
        code: { type: integer }
```

完整断言实现见 `core/asserter.py`；新增类型请同步修改 `enums/assert_type.py` 与 `asserter`。

### 4.4 HTTP 与其它枚举（摘录）

- **请求方法**：`enums/request/method.py` → `GET`、`POST`、`PUT`、`DELETE`、`PATCH` 等。
- **Pytest 标记**（`pytest.ini`）：`p0` / `p1` / `p2`、`wms`、`rms`、`pda` — 在场景或步骤上通过 pytest 收集层打标（按项目约定扩展）。

---

## 5. Hook 函数配置说明

### 5.1 机制说明

- Hook 在 YAML 中以 **`${函数名(参数)}`** 出现，由 `utils/parsing_manage/hook_executor.py` 解析。
- 仅允许调用 **`extensions/`** 包内各模块的**公开函数**（名称不以 `_` 开头）；`eval` 运行在沙箱中（`__builtins__` 禁用，仅注入 `settings` 与注册函数）。
- **`debugtalk.py`** 用于显式导出常用函数，便于查阅；实际执行以 `hook_executor` 自动扫描 `extensions` 为准。

### 5.2 内置 Hook 一览

| 函数 | 模块 | 作用 |
|------|------|------|
| `rms_login_username()` / `rms_login_password()` | common_funcs | 读取 `rms_login_test_account` |
| `wms_login_username()` / `wms_login_password()` | common_funcs | 读取 `wms_login_test_account` |
| `gen_order_no(prefix='AUTO')` | common_funcs | 生成唯一订单号 |
| `get_env(name, default='')` | common_funcs | 读进程环境变量 |
| `current_time()` / `random_phone()` / `random_name()` | common_funcs | 时间、Faker 数据 |
| `wait_rms_task_status(...)` | rms_funcs | 轮询 RMS 任务状态 |
| `build_pick_payload(...)` | pda_funcs | 组装 PDA 拣货请求体 |
| （WMS 相关） | wms_funcs | Token、订单号等业务封装 |

在 YAML 中建议对含 Hook 的字符串加引号，避免 `{}` 被 YAML 解析歧义：

```yaml
username: '${rms_login_username()}'
order_sn: '${gen_order_no("WH")}'
```

### 5.3 新增 Hook 步骤

1. 在 `extensions/` 对应域模块中新增 **普通函数**（勿以下划线开头）。
2. 本地执行任一场景，确认 `${your_func()}` 可解析。
3. （可选）在 `debugtalk.py` 的 `__all__` 中导出，方便团队发现。

```python
# extensions/common_funcs.py
def warehouse_code(prefix: str = "WH") -> str:
    return f"{prefix}_{gen_order_no()}"
```

```yaml
variables:
  code: '${warehouse_code("RMS")}'
```

### 5.4 与 `setup_hooks` / `teardown_hooks` 的区别

`StepModel` 中预留了 `setup_hooks` / `teardown_hooks` 字段（函数名字符串列表），用于步骤级前置/后置扩展；**当前场景执行器尚未接入**，请优先使用 `${}` Hook 与多步骤场景表达依赖关系。

---

## 6. 其它说明

### 6.1 Allure 报告

- 原始结果：`reports/allure_results`（`pytest.ini` 与 `run.py` 默认 `--clean-alluredir`）。
- 静态 HTML：`allure generate reports/allure_results -o reports/html_report --clean`
- `python run.py -S`：测试结束且终端摘要/通知完成后，在 `pytest_unconfigure` 中启动 `allure serve`，避免阻塞通知。

### 6.2 日志

- 目录：`logs/`，按日期与级别滚动（见 `utils/logger.py`）。

### 6.3 从 Postman 迁移 API

```bash
uv run python -m utils.data_manage.postman <collection.json> --out api/wms
```

生成草稿后需人工校对 URL、字段名与断言。

### 6.4 参考文档

- `doc/reference/playbook.md` — Pytest / 工程化实践摘录  
- `doc/reference/advanced-patterns.md` — 进阶模式说明  
- 模板：`testcases/template_api.yaml`、`testcases/template_flow.yaml`

### 6.5 常见问题

| 现象 | 处理建议 |
|------|----------|
| `base_url` 无法解析 | 确认 API 路径为 `api/wms/`、`api/rms/` 等，且 `env.*.yaml` 中 `base_urls` 已配置 |
| 失败响应仍报 JSONPath | 将 `extract` 放在 `validate` 通过之后；登录类接口勿在 API 层统一 extract |
| IDE 找不到 `allure` | 设置 `ALLURE_CMD` 或安装 Allure CLI 并加入 PATH |
| RMS 登录 400 | 请求体字段需驼峰 `userName`（见 `api/rms/login.yaml`） |

---

## License

内部项目，按团队规范使用与分发。
