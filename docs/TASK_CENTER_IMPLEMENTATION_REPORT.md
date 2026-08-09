# 统一任务中心后端基础：实现报告

## 范围

本工作包建立跨模块任务中心的最小后端基础。它提供持久化任务记录和读取 API，但不伪造后台执行、实时进度或任务完成结果。

## 已实现

- 新增 `task_records` 数据表，包含任务类型、标题、状态、进度、来源上下文、受限详情、错误、重试次数和时间戳；
- 新增 `TaskStatus`：`pending`、`running`、`succeeded`、`failed`、`cancelled`、`awaiting_confirmation`；
- 新增 API：
  - `POST /api/v1/tasks`
  - `GET /api/v1/tasks`
  - `GET /api/v1/tasks/{task_id}`
- 支持按状态筛选和分页；
- 已将任务模型注册到 SQLAlchemy 元数据，将路由注册到 API v1；
- 新增 Alembic 迁移 `d4e5f6a7b8c9_add_task_records.py`。

## 关键文件

- `app/modules/task/model.py`
- `app/modules/task/schema.py`
- `app/modules/task/repository.py`
- `app/modules/task/service.py`
- `app/modules/task/router.py`
- `alembic/versions/d4e5f6a7b8c9_add_task_records.py`
- `tests/modules/task/test_task_api.py`

## 真实能力边界

本轮只完成任务中心的持久化和查询基础，尚未完成：

- 将既有文档、检索、分析、写作、矩阵任务自动镜像到该表；
- 后台 Worker、队列、取消、重试、依赖编排；
- 任务执行日志或 SSE/WebSocket 进度推送；
- Agent 和评测执行器。

因此，`POST /api/v1/tasks` 创建的是待执行记录，不会声称任务已经在后台运行或完成。

## 实际验证

已运行：

```text
pytest tests/modules/task/test_task_api.py tests/test_database.py -q
```

结果：`5 passed`，另有一条 FastAPI TestClient 的依赖弃用警告。

已运行：

```text
alembic check
```

结果：`No new upgrade operations detected.`

未完成：

```text
ruff check ...
```

原因：当前 `med-research-ai` Python 环境未安装 Ruff，命令返回 `No module named ruff`。本报告不将 Ruff 标记为通过。

## 迁移修正

实现过程中发现 `c1d2e3f4a5b6` 已被现有“文献检索任务”迁移占用；为避免 Alembic revision 冲突，新增任务中心迁移使用唯一编号 `d4e5f6a7b8c9`，并以当前 head `b3c4d5e6f7a8` 为前置迁移。
