# R3 实施状态

## R3-WP01 — 研究条件输入模型

- 已新增 `/api/v1/research-conditions` 的创建、读取与增量更新接口。
- 研究条件以不可变版本快照保存；`PATCH` 生成递增的 `conditions_version`。
- 每个已提交条件字段保存 `value`、`known` 与 `source`。`known=false` 仅接受 `source=unknown` 和空值，并可由后续候选方向流程通过 `exclude_unknown_fields` 排除，避免模型擅自补全。
- 可开展类型仅允许 `clinical`、`animal`、`cell`、`bioinformatics`；不确定项单独保存为 `uncertain_notes`。
- 本工作包未引入模型调用、模型 provider 路由或前端表单；后者待前端工作包实现。

## R3-WP02 — 研究主题与问题结构化

- 新增 `/api/v1/topic-structuring/parse`、读取和 PATCH 接口：原始主题不可覆盖，结构化与每次编辑均保存不可变版本，可返回版本序列供比较。
- 复用 R2-WP02 `disease`、`intervention`、`target`、`mechanism` 字段；仅新增 `comparator`、`outcome` 与 `study_type`，避免第二套 PICO 基础字段。
- 纯函数守卫支持 `pico`、`peco`、`mechanism`、`unstructured`；不完整模板被降级为 `unstructured`，保留原始主题、原因与核心关注点，不硬套 PICO。
- 澄清问题绑定可编辑字段；答案回填字段并记录 `known_fields[field]=true`。`general` 问题只标记已回答，不臆测字段。
- 公开主题解析支持显式 `model_config_id`；未指定时仅选择已授权内容出境的外部配置。不会使用全局 provider，也不会在 Ollama 失败时静默切云端。前端需在发往云端前展示隐私提示。【待前端工作包】

## R3-WP03 — 热点、争议与证据缺口

- 新增 `POST /api/v1/evidence-analysis/analyze`：基于一个现有证据矩阵按需生成分析，不持久化模型结论，避免结果脱离矩阵当前版本。
- 输出严格分为统计层和解读层。统计层为纯函数，提供主题频次、样本量受限的趋势、研究类型分布；解读层必须逐项绑定矩阵中存在的 PMID/DOI 来源，并精确引用统计层条目。
- 请求和响应记录检索范围、检索日期、矩阵版本与文献数量。研究类型随统计与解读一起返回，提示调用方不能把综述与原始研究直接当作同等级结论。
- 分析会将矩阵字段与用户笔记作为解读上下文；含用户笔记时默认只选择 Ollama，本地模型不存在时显式提示安装 Ollama 或明确选择云端配置。公开矩阵分析默认只选择已允许内容出境的外部配置；没有符合条件的模型时显式报错，不会静默转发到云端。前端尚未实现云端数据出境提示。【待前端工作包】
