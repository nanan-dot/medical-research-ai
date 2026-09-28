# Agent 证据与人工审批验收

本任务继承 WP6–WP9 的证据、数字绑定、追溯与工程效果边界。以下为实现前冻结的行为要求；确定性适配器数据只用于测试。

| AC | Given / When / Then | 测试 |
| --- | --- | --- |
| A1 | 缺少或不足证据，运行后必须失败 | test_rejects_unsafe_evidence |
| A2 | 悬空、伪造来源或空 Claim，运行后必须失败 | test_rejects_unsafe_evidence |
| A3 | 数字未核验、绑定错误，运行后必须失败 | test_rejects_unsafe_evidence |
| A4 | 冲突、写作、方向或拟发布任务，运行后必须 interrupt；批准后仍须通过证据门 | test_required_approval |
| A5 | 等待审批时拒绝或取消，必须形成独立终态且不执行引用检查 | test_stop_decisions |
| A6 | 真实适配器输出来源与 trace_id，执行后每个关键节点可回放且轨迹无正文 | test_persistent_replay |
| A7 | 重建服务后查询和审批，运行、审批及轨迹可恢复 | test_persistent_replay |
| A8 | 请求无效、运行缺失、重复审批，API 分别返回 422、404、409；创建 201 | test_api_contract |
| A9 | 适配器不可用或失败，安全失败且不伪造输出 | test_default_adapter_fails_closed |
| A10 | Agent 页面提交、审批、取消与加载轨迹，调用真实 API 并显示失败状态 | AgentView.test.ts |

既有 23 个 Agent 测试基线实际通过；其中允许字符串证据完成及无证据写作完成的旧断言须按本次安全契约更新。
