# 正式医学 Shadow 标注、冻结与发布指南

## 数据集契约

每行 JSONL 是一个 `MedicalShadowCase`。正式记录必须为 `label_source="expert_annotation"`，并包含：匿名 `case_id`、`dataset_version`、PICO/问题类型、候选 `document_id`/`chunk_id`/来源标识、0–3 相关性、`direct|indirect|excluded` 证据角色、可选数字/单位、否定语义、引用与数字核验标签、两位匿名标注者及裁决状态。`synthetic_demo` 仅用于演示和测试，永远不能用于发布判定。

```json
{"case_id":"demo-001","dataset_version":"demo-v1","label_source":"synthetic_demo","frozen":false,"question_type":"therapy","pico":{"population":"synthetic","intervention":"sotorasib"},"candidates":[{"document_id":"demo-doc","chunk_id":"demo-chunk","source_identifier":"demo:1","relevance":3,"evidence_role":"direct","numeric_value":"10","numeric_unit":"months","negated":false,"citation_supported":true,"numeric_verified":true}],"annotators":[{"anonymous_id":"expert-a","status":"complete"}],"adjudication_status":"pending"}
```

不得输入 PHI、姓名、电话、身份证号、住院号或病历号。正式导入使用 `validate_formal_case`；拒绝信息只包含 `case_id` 和字段类别，不回显敏感原文。

## 标注与裁决

1. 两名医学专家独立标注同一冻结候选集，不调整 baseline/candidate 候选或其身份。
2. 对直接证据、间接证据和排除证据分别标注；不同人群、时间点、单位或否定语义不得合并。
3. 标注完成后处理分歧、记录裁决，再将 `adjudication_status` 改为 `complete`。
4. 冻结版本、候选集、索引/模型版本和运行 seed；冻结后创建不可变 Shadow 报告 ID。

## 运行与解释

`MedicalShadowRunner` 对同一 `case_id` 的 baseline 和 candidate order 计算 nDCG@10/20、MRR、Recall@50、P@10、排除证据精确率；有标签时额外计算引用支持率/数字核验率。没有标签时指标是 `unavailable`，不是零。Bootstrap 使用固定 seed；未冻结、非专家、未裁决或样本不足的报告均为 `exploratory`，不得发布。

性能预算默认未批准：`MEDICAL_SHADOW_PERFORMANCE_BUDGET_APPROVED=false`。审批方必须冻结冷启动、warm 单查询、Top-K、批量、并发、p50/p95/p99、可可靠测量时的 RSS 与失败率，并在 `..._SOURCE` 记录批准来源；本机单样例不能代替该预算。

## 发布与回滚

只有冻结专家数据集、裁决、效果门、安全/引用门、已批准性能预算及冻结真实 Shadow 报告全部满足时，发布门才可能为 true。任何缺失都会列为结构化原因。默认继续 PaperQA2 且 `GROUNDED_RAG_ENABLED=false`。回滚即关闭新链 feature flag，保留审计记录；无需修改系统服务或环境变量。

## AC → Test

| AC | 验收 | 测试 |
| --- | --- | --- |
| AC-MS-01 | 版本化专家/合成标注契约与候选身份 | `test_medical_shadow.py::test_shadow_runner_compares_same_frozen_candidates_and_marks_missing_labels_unavailable` |
| AC-MS-02 | 同一冻结候选集比较、检索指标与缺失标签 unavailable | 同上 |
| AC-MS-03 | 固定 seed bootstrap CI、非正式数据 exploratory | 同上 |
| AC-MS-04 | PHI 阻止且不回显原文 | `test_formal_case_rejects_phi_without_exposing_original_text` |
| AC-MS-05 | 性能预算默认未批准 | `tests/test_medical_shadow_config.py` |
| AC-MS-06 | 发布门不可绕过 | `test_release_gate_requires_frozen_expert_dataset_adjudication_metrics_budget_and_report` |
| AC-MS-07 | 默认链路与真实效果边界 | `tests/rag/test_shadow_release.py`、本文档 |
