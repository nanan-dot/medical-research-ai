# M0 公共基础设施实现与验收报告 V1.5

状态：`FROZEN（M0 公共基础设施最终基线）`
日期：2026-09-16
迁移 head：`m0j1e2f3a4b5`

## 1. 冻结结论

M0 剩余工程项已闭环，当前允许进入 M1 A1 开发。冻结范围包括：公共 Run/Step 状态机、授权与预算、外部执行账本、恢复裁决、Artifact 版本与失效传播、Confirmation、outbox、SQLite 正式事务以及旧运行时隔离。

本结论覆盖 M0 公共基础设施。A1—A5 领域能力、医学有效性和整仓生产发布仍执行各自门禁。

## 2. 本版完成的修复

### 2.1 类型安全

修复 `app/agents` 中 24 条 mypy 错误：

- SQLAlchemy 更新结果显式收窄为 `CursorResult`；
- RevisionResolver 使用明确的可修订记录联合类型；
- ArtifactRef 从数据库字符串通过 Pydantic 权威校验恢复；
- AgentGraphState 补全 execution，并在旧 JSON 读取边界执行类型校验；
- QueryPlan、TraceEvent 和可空 ResearchContext 类型完成收口。

最终 `mypy app/agents --follow-imports=silent`：46 个源文件，0 error。

### 2.2 外部执行确定顺序

`agent_external_executions` 新增 `execution_seq`：

- 同一个 Run 内从 1 单调递增；
- 数据库约束 `UNIQUE(run_id, execution_seq)` 和 `execution_seq >= 1`；
- 旧数据按 SQLite 插入 rowid 确定性回填；
- Recovery 只按 `execution_seq DESC` 选择最新 execution，不再依赖时间戳或 UUID；
- 对抗测试把较旧 execution 的 `created_at` 设为未来时间，仍验证 Recovery 选择 sequence 最大者。

### 2.3 审计引用删除保护

迁移 `m0j1e2f3a4b5` 为 SQLite 增加显式保留策略：

- execution 账本禁止删除；
- execution 的身份字段禁止修改；
- 被 execution 引用的 Run、Step、Authorization、BudgetReservation、Idempotency 和正式 Artifact 禁止删除或修改主身份；
- 迁移测试验证旧 execution 回填 sequence，并验证删除操作由数据库拒绝。

这是一套数据库级删除保护策略，适用于当前 SQLite 部署。

### 2.4 旧运行时彻底隔离

- 旧 HTTP 创建、审批、取消入口继续返回 410；
- `AgentRunService.start/resume` 默认拒绝写入；
- 仅历史兼容测试能显式传入 `allow_legacy_writes=True`；
- 生产代码扫描未发现该测试能力开关；
- 新增服务层对抗测试，证明绕过 HTTP 直接调用也不能写旧 JSON Run。

### 2.5 测试依赖与网络故障

- `httpx2 2.13.0` 限定在 dev 依赖，用于 Starlette TestClient transport；
- 生产 Provider 仍使用 `httpx 0.28.1`；
- TestClient 以 `-W error` 导入，无弃用 warning；
- TCP 故障测试覆盖 timeout、disconnect、truncated response；
- 三类故障均进入 `outcome_unknown + recovery_required`，预算预留保持 active，不会盲目重试。

### 2.6 SQLite 竞争与真实 Provider

- 4 个独立进程各执行 20 次 `BEGIN IMMEDIATE` 写事务，最终 80 次写入无丢失；
- 实际启动本机 Ollama 0.32.15；
- 验证已配置模型存在；
- 执行一次最小真实推理，请求成功、响应非空、Provider 返回 done，耗时 4.93 秒；
- 验收后已停止本轮启动的 Ollama 服务。

真实云 Provider 的厂商计费和远端对账属于具体 Provider 接入验收；M0 的通用发送、失败和恢复语义已由真实 TCP 故障与本机真实 Provider 调用验证。

## 3. 最终验证结果

解释器：`F:\software\programme\Anaconda\envs\med-research-ai\python.exe`
运行前清空 `PYTHONPATH`。

| 门禁 | 最终实测结果 |
|---|---|
| M0 专项、对抗、迁移、冻结补强 | `55 passed in 181.55s` |
| Agent、数据库、ResearchContext 扩展回归 | `100 passed in 189.41s` |
| 单调 sequence 选择专项 | `1 passed` |
| Ruff | All checks passed |
| mypy app/agents | 46 files，0 issues |
| compileall app/agents | 通过 |
| pip check | No broken requirements found |
| uv lock --check | 通过，163 packages |
| Alembic heads / current | 唯一 `m0j1e2f3a4b5 (head)` |
| 实际数据库 execution_seq 空值 | 0 |
| 实际数据库 M0 保留触发器 | 14 |
| 生产 app/agents create_all 扫描 | 0 |
| 生产 allow_legacy_writes=True 扫描 | 0 |
| TestClient warning 门禁 | 通过 |
| 本机真实 Ollama 调用 | 通过 |

## 4. 数据库升级与恢复点

实际数据库已由 `m0i1d2e3f4a5` 升级至 `m0j1e2f3a4b5`。

升级前备份：

`D:\AI_project\rag_medicine\data\app.pre-m0j-2026-09-16.db`

备份 SHA-256：

`951BC8BE4CD823D49EB0DEB7EE19A9259044B52A8E780462E198BA54CCE7C86C`

升级后数据库 SHA-256：

`5121B871AE5BF96ACE0C05D7DA099CEB1AEA9063CBC8FAE2087F91A5647B65D2`

备份可用于恢复升级前状态；恢复时须先停止应用并另行保留当前数据库。

## 5. 冻结源码快照

文件：`M0_V1.5_2026-09-16_source.tar`

SHA-256：

`BC0733C0D2EB3657613CDD248E2AB02DA4AEAC96D1ED8EB860EE5DF4CEC32564`

归档共 714 项，包含运行所需 Python 源码、Alembic 迁移、Agent/ResearchContext 测试、数据库测试、`pyproject.toml`、`uv.lock` 和 `alembic.ini`。归档不含 `.env`、API 密钥、用户论文和数据库。

工作树还包含其他项目任务的改动，未把整个工作树误标为 M0。参考 Git HEAD 为 `7f0ac79dd51e33d89022b3d13a6d9872fb9dfdf4`，精确冻结身份以源码归档 SHA-256 为准。

## 6. 冻结守恒规则

M1 A1 及后续 Agent 必须遵守：

1. 只能使用公共 Run/Step 状态和合法转换；
2. 模型调用必须先完成授权、预算预留和 execution prepare；
3. 发送后不确定结果必须进入 `outcome_unknown`，不得自动伪造成功；
4. 下游只能读取带 ID、版本和 hash 的有效正式 Artifact；
5. 上游替代必须传播失效并 supersede 全部相关 pending Confirmation；
6. 旧 JSON Run 只能读取，不能作为正式交接或新增写入口；
7. 任何删除不能破坏已存在 execution 的审计身份链。

## 7. 重新复审条件

以下任一变化都必须建立新 M0 版本并重跑门禁：

- 公共 Run/Step/execution 状态机；
- Recovery 最新执行选择或成功裁决；
- 授权、预算、幂等或事务边界；
- Artifact 注册、版本、依赖和失效传播；
- Confirmation 消费或 outbox 一致性；
- execution 审计保留策略；
- SQLite 迁移 head；
- FastAPI/Starlette/httpx/httpx2/SQLAlchemy 的相关版本变化。

## 8. 最终决定

- M0：`FROZEN`
- 是否允许进入 M1 A1：是
- 是否存在已知 M0 冻结阻塞：否
- 下一步：按 A1 冻结设计编写 M1 A1 验收清单和实现

本轮使用 acceptance-testing 将每项结论绑定到可执行门禁；使用 prism-scan 检查外部调用时序、恢复权威链和传递失效的守恒关系。
