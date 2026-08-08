# R3 实施状态

## R3-WP01 — 研究条件输入模型

- 已新增 `/api/v1/research-conditions` 的创建、读取与增量更新接口。
- 研究条件以不可变版本快照保存；`PATCH` 生成递增的 `conditions_version`。
- 每个已提交条件字段保存 `value`、`known` 与 `source`。`known=false` 仅接受 `source=unknown` 和空值，并可由后续候选方向流程通过 `exclude_unknown_fields` 排除，避免模型擅自补全。
- 可开展类型仅允许 `clinical`、`animal`、`cell`、`bioinformatics`；不确定项单独保存为 `uncertain_notes`。
- 本工作包未引入模型调用、模型 provider 路由或前端表单；后者待前端工作包实现。
