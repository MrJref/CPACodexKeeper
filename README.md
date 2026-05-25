# CPACodexKeeper

[![CI](https://github.com/5345asda/CPACodexKeeper/actions/workflows/ci.yml/badge.svg)](https://github.com/5345asda/CPACodexKeeper/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)

[中文](README.md) | [English](README.en.md)

CPACodexKeeper 是一个用于**巡检和维护 CPA 管理端中的 codex token** 的 Python 工具。

它的目标不是生成 token，而是对**已经存储在 CPA 管理 API 中的 codex token** 做持续维护。

## 核心能力

- 检查 token 是否失效
- 按实际返回的 quota 窗口自动禁用或启用
- 可选地刷新已禁用且即将过期的 token
- 支持 `config.yml`、`.env`、Docker 和 GitHub Actions CI

## 适合谁用

如果你已经有一个 CPA 管理 API，并且希望：

- 定期清理失效 token
- 控制 token 的 usage 配额占用
- 在额度恢复后自动启用 token
- 在需要时对已禁用且临近过期 token 启用自动刷新

那么这个项目就是为这个场景准备的。

## 快速开始

```bash
cp .env.example .env
python main.py --once
```

更多配置和运行方式见下文。

---

## 1. 项目解决什么问题

在实际使用中，codex token 往往不是静态资源，而是会随着时间推移出现以下情况：

- token 已失效，但仍残留在管理端
- token 的 usage 配额已经耗尽，不适合继续分发
- token 已被手动禁用，但额度恢复后没有自动启用
- token 快过期了，在明确允许刷新时需要对已禁用项提前刷新
- team 账号和非 team 账号的 usage 返回结构不同，需要统一处理

CPACodexKeeper 会把这些维护动作自动化，减少人工巡检和手工清理。

---

## 2. 当前维护逻辑

每轮巡检中，程序会按下面的顺序处理：

1. 从 CPA 管理 API 拉取 token 列表
2. 只保留 `type=codex` 的 token
3. 逐个获取 token 详情
4. 读取 token 过期时间和剩余有效期
5. 调用 OpenAI usage 接口检查可用性和限额
6. 如果 usage 返回 `401` 或 `402`，则先使用 `refresh_token` 尝试刷新复活
7. 复活刷新成功后会上传最新 token 数据，并二次检测 usage；二次检测通过才继续后续限额策略
8. 如果没有 `refresh_token`、刷新失败、上传失败，或二次检测仍返回 `401` / `402`，则按死号策略删除或禁用
9. 如果 usage 返回中包含两个 quota 窗口，则按窗口实际含义判断
10. 只要任一窗口剩余额度小于阈值，就会禁用；只有两个窗口剩余额度都不低于阈值时才会重新启用
11. 如果 token **没有 `refresh_token`**，并且已经过期，则直接删除
12. 如果 token **没有 `refresh_token`**，并且剩余额度小于阈值，则直接删除
13. 如果显式启用了自动刷新，并且 token 在当前轮处理后仍是禁用状态且临近过期，则尝试刷新
14. 刷新成功后将最新 token 数据上传回 CPA

这是一个**按轮次运行、轮内可并发**的流程：一轮结束后才会进入下一轮，但同一轮中的多个 token 可以并发巡检。

---

## 3. 支持的限额判断规则

项目已经兼容 team 模式和普通模式。

### Team 模式

如果 usage 返回中包含周限额窗口：

- `rate_limit.primary_window`：通常表示主 quota 窗口，日志会按 `limit_window_seconds` 自动显示为 `5h`、`Week` 等正确标签
- `rate_limit.secondary_window`：通常表示次 quota 窗口，日志同样按 `limit_window_seconds` 自动显示正确标签

此时程序会：

- 同时检查 `primary_window.used_percent` 与 `secondary_window.used_percent` 并换算剩余额度
- 只要任一窗口剩余额度小于阈值，就会触发禁用
- 只有两个窗口剩余额度都不低于阈值时，已禁用 token 才会被重新启用
- 自动携带 `Chatgpt-Account-Id` 请求头

### 非 Team / 无周限额模式

如果 usage 中没有周限额窗口：

- 程序会回退到 `primary_window.used_percent` 并换算剩余额度进行判断

### 默认阈值

默认：

- `CPA_QUOTA_THRESHOLD=1`

也就是：

- 剩余额度低于 1% 时才禁用，也就是通常的 0% 耗尽场景
- 配置为 `30` 时表示剩余额度小于 30% 就禁用，不低于 30% 时可重新启用
- 但如果 token 没有 `refresh_token`，剩余额度达到阈值时会直接删除，而不是仅禁用

---

## 4. 配置方式

项目支持 `config.yml`、环境变量和 `.env`。优先级从高到低：

1. `config.yml`
2. 环境变量，包括 `docker-compose.yml` 注入的配置
3. `.env`
4. 默认值

仓库内的 `config.yml` 默认是全注释模板，不会覆盖环境变量。需要让页面和运行策略通过配置文件调整时，取消注释并填写对应字段即可。

也可以继续复制 `.env` 模板：

```bash
cp .env.example .env
```

然后编辑 `.env`，或直接编辑 `config.yml`。

### 配置项说明

- `CPA_ENDPOINT`：CPA 管理 API 地址
- `CPA_TOKEN`：CPA 管理 token
- `CPA_PROXY`：可选代理
- `CPA_CRON`：守护模式自动巡检 cron，使用 6 位格式 `秒 分 时 日 月 星期`，默认 `0 0/10 * * * ?`
- `CPA_INTERVAL_MIN` / `CPA_INTERVAL_MAX`：可选 Cron 随机偏移窗口，支持秒数或 `s/m/h/d` 后缀；`CPA_INTERVAL_MIN` 表示最多提前多久，`CPA_INTERVAL_MAX` 表示最多延后多久，例如 Cron 命中 `12:00:00`、下限 `8m`、上限 `2m` 时，会在 `11:52:00` 至 `12:02:00` 之间随机执行
- `CPA_QUOTA_THRESHOLD`：剩余额度禁用阈值，默认 `1`；例如 `30` 表示剩余额度小于 30% 时禁用
- `CPA_EXPIRY_THRESHOLD_DAYS`：禁用 token 的刷新阈值天数，默认 `3`
- `CPA_ENABLE_REFRESH`：是否启用对禁用 token 的自动刷新，默认 `true`
- `CPA_ENABLE_AUTO_DELETE`：是否启用自动删除，默认 `true`；设为 `false` 时原本会删除的 token 改为禁用
- `CPA_HTTP_TIMEOUT`：CPA API 请求超时秒数，默认 `30`
- `CPA_USAGE_TIMEOUT`：OpenAI usage 请求超时秒数，默认 `15`
- `CPA_MAX_RETRIES`：临时网络 / 5xx 错误重试次数，默认 `2`
- `CPA_WORKER_THREADS`：单轮巡检的并发线程数，默认 `8`
- `WEBUI_ENABLED`：是否启动内置 WebUI，默认 `false`；`docker-compose.yml` 默认设为 `true`
- `APP_HOST`：WebUI 监听地址，默认 `0.0.0.0`
- `APP_PORT`：WebUI 监听端口，默认 `8765`
- `LOG_MAX_LINES`：WebUI 最近日志内存保留最大行数，默认 `500`
- `AUTH_ENABLED`：是否启用 WebUI 登录保护，默认 `false`
- `LOGIN_PASSWORD`：启用 `AUTH_ENABLED=true` 时必填的登录密码
- `AUTH_SESSION_TTL`：登录 session 有效期，默认 `168h`，支持 `s/m/h/d` 后缀

推荐直接参考 `config.yml` 或 `.env.example` 中的注释填写。

默认开启自动刷新，但 keeper 仍只会刷新当前轮处理后仍处于禁用状态的 token；启用状态 token 交给 CPA 自己的自动刷新逻辑处理。如果你需要避免与其他刷新写入方竞争，可以在 `config.yml` 或 `.env` 里显式设成 `false`。

---

## 5. 运行方式

### 环境要求

- Python 3.11+
- 依赖：`curl-cffi`

安装依赖：

```bash
pip install -r requirements.txt
```

### 单次执行

适合手动巡检、调试或配合外部调度器使用：

```bash
cp .env.example .env
python main.py --once
```

### 守护模式

适合持续运行：

```bash
python main.py
```

### WebUI

内置 WebUI 会沿用守护模式巡检，并提供状态面板、最近日志、清空日志、手动触发巡检、代理延迟检测和 `config.yml` 热更新配置：

```bash
WEBUI_ENABLED=true python main.py
```

也可以用命令行覆盖配置：

```bash
python main.py --web
python main.py --no-web
```

如果公开访问，建议设置：

```env
AUTH_ENABLED=true
LOGIN_PASSWORD=replace-with-a-strong-password
AUTH_SESSION_TTL=168h
```

### 演练模式

不会真正删除、禁用、启用或上传更新：

```bash
python main.py --once --dry-run
```

---

## 6. Docker 部署

项目支持通过 Docker 运行。`docker-compose.yml` 会以可写方式挂载 `./config.yml` 到容器内，便于 WebUI 保存配置；且 `config.yml` 的优先级高于 Compose 注入的环境变量。

### 构建镜像

```bash
docker build -t cpacodexkeeper .
```

### 直接运行

```bash
docker run -d \
  --name cpacodexkeeper \
  -p 8765:8765 \
  -e CPA_ENDPOINT=https://your-cpa-endpoint \
  -e CPA_TOKEN=your-management-token \
  -e 'CPA_CRON=0 0/10 * * * ?' \
  -e WEBUI_ENABLED=true \
  -e LOG_MAX_LINES=500 \
  -e AUTH_ENABLED=true \
  -e LOGIN_PASSWORD=replace-with-a-strong-password \
  cpacodexkeeper
```

### 使用 Compose

先复制模板：

```bash
cp .env.example .env
```

然后编辑 `.env` 或 `config.yml`，再启动：

```bash
docker compose up -d --build
```

Compose 默认映射 `${APP_PORT:-8765}` 并启用 `WEBUI_ENABLED=true`。如果 `config.yml` 中配置了 `webui.port` 或 `APP_PORT`，应用内部端口会使用配置文件值；端口映射仍由 Compose 启动时的 `${APP_PORT:-8765}` 决定。启动后访问：

```text
http://localhost:8765
```

---

## 7. 输出与行为说明

程序会为每个 token 输出一段巡检日志，通常包含：

- 同一轮内可以并发巡检多个 token
- 但每个 token 的日志会缓冲后一次性输出，避免多线程下控制台内容交错

- token 名称
- 邮箱
- 当前禁用状态
- 过期时间
- 剩余有效期
- usage 检查结果
- 实际 quota 窗口信息
- 是否被删除、禁用、启用或刷新

在每轮结束后，还会输出汇总统计，例如：

- 总计
- 存活
- 死号（已删除）
- 已禁用
- 已启用
- 已刷新
- 跳过
- 网络失败
- 完成时间（`yyyy-MM-dd HH:mm:ss`）

---

## 8. 健壮性设计

当前版本已经补了几项关键保护：

- 启动时强校验配置
- 对数值配置做范围检查
- 对 CPA API 和 usage API 设置独立超时
- 对临时网络错误和 5xx 做有限重试
- 对 `secondary_window = null` 做安全回退
- 单个 token 失败不会中断整轮任务
- 守护模式下单轮报错不会导致整个进程退出

---

## 9. 开发辅助

项目内置了 `justfile`，方便统一常用命令。

如果你安装了 `just`，可以直接使用：

```bash
just install
just test
just run-once
just dry-run
just daemon
just docker-build
just docker-up
just docker-down
```

---

## 10. 测试与 CI

### 本地测试

```bash
python -m unittest discover -s tests
```

或者：

```bash
just test
```

### GitHub Actions

项目已包含 CI 工作流：

- 自动运行单元测试
- 自动验证 Docker 镜像可以构建

工作流文件：

```text
.github/workflows/ci.yml
```

---

## 11. 项目结构

```text
CPACodexKeeper/
├─ src/
│  ├─ cli.py
│  ├─ cpa_client.py
│  ├─ logging_utils.py
│  ├─ maintainer.py
│  ├─ models.py
│  ├─ openai_client.py
│  ├─ settings.py
│  └─ utils.py
├─ tests/
├─ config.yml
├─ .env.example
├─ docker-compose.yml
├─ Dockerfile
├─ justfile
├─ main.py
├─ README.md
└─ README.en.md
```

---

## 12. 故障排查

### 启动时报配置错误

通常是 `config.yml` / `.env` 缺字段，或者字段格式不对。

重点检查：

- `CPA_ENDPOINT`
- `CPA_TOKEN`
- 数值项是否为合法整数

### usage 返回 `401`

表示当前 access token 已无效。当前逻辑会先使用 `refresh_token` 尝试刷新复活，刷新并二次检测成功后会继续保留；复活失败才按死号策略删除或禁用。

### usage 返回 `402`

通常表示 workspace 已停用或不可用。当前逻辑同样会先尝试刷新复活；如果刷新失败或二次检测仍失败，才按死号策略删除或禁用。

### `secondary_window = null`

表示没有周限额窗口。程序会自动回退到主窗口判断。

### Docker 无法本地构建

先确认本机是否安装并启用了 Docker CLI。

---

## 13. 适用范围说明

这个项目面向**已授权的内部维护场景**，适合：

- 私有 CPA 管理系统
- 内部 token 池维护
- 已获得授权的自动巡检和清理任务

不建议将真实凭据提交到版本控制中。真实 `config.yml` 或 `.env` 应保留在本地或安全的部署环境中。
