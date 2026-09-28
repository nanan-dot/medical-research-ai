# Codex 执行提示词：文献推荐理由双通道成熟化

请在本机仓库 `D:\AI_project\rag_medicine` 中直接实施“确定性推荐理由 + 非阻塞模型润色”完整方案。

## 一、工作方式与边界

1. 先完整读取本提示词、`AGENTS.md`、`docs/CODE_STANDARDS.md`，以及文献推荐相关的后端、前端、迁移和测试。
2. 当前工作区存在大量用户和其他任务的未提交修改。必须保留并最小合并；禁止 `reset`、`checkout`、`clean`、删除目录或覆盖无关资产。若目标文件在实施期间发生变化，重新读取后合并。
3. 使用验收测试驱动：先把 AC-RR-01～14 映射为行为测试，确认关键新增测试在实现前失败，再实施并持续验证。
4. 范围仅限文献推荐理由生成、模型润色状态、必要的推荐契约/迁移/测试及推荐页状态展示。不得重构其他页面，不得伪造论文、PMID、DOI、医学结论或商业指标。
5. 正式推荐的选择、去重、覆盖判断、排序和评分不得依赖语言模型。语言模型只能改写已生成的结构化基础理由。
6. 未经用户再次授权，不升级或写入正式数据库；迁移仅在临时数据库验证。若现有代码已经包含部分实现，先审计，不得假设其正确或完整。
7. 除非存在无法安全解决的真实并发冲突或必须由用户提供的数据，否则持续执行到所有验收门禁通过，不停留在阶段性报告。

## 二、目标架构

实现两条解耦通道：

```text
真实候选与可核验元数据
  -> 确定性特征与事实原子
  -> RecommendationReasonFactPacket v1
  -> 规则引擎生成 base_reason
  -> 保存候选并立即激活推荐运行
  -> 前端立即展示 base_reason
  -> 后台异步对有限候选执行模型润色
  -> 严格校验 polished_reason
     -> 通过：原子更新展示理由
     -> 超时/不可用/不合规：保留 base_reason
```

模型润色失败不是推荐运行失败，不得把活动推荐恢复为 running/failed，不得阻塞列表、历史、接受/忽略等操作。

## 三、严格事实包契约

新增版本化、可序列化、可测试的 `RecommendationReasonFactPacket`，至少包含：

- `schema_version = recommendation-reason-facts-v1`
- `language`
- `generation_mode`: `intent_bound | exploration`
- `recommendation_context`
  - `source_result_id`
  - `intent_snapshot_id`
  - `exploration_query`
  - `recommendation_mode`
- `article_evidence`
  - 元数据可用状态
  - 发表年份（仅真实存在时）
  - 标准化研究设计
  - 研究设计核验状态及其 `fact_ids`
- `topic_matches[]`
  - 唯一 `fact_id`
  - 维度与中文标签
  - `matched | partial | unavailable`
  - 标准化术语
  - 确定性展示文本
  - 来源字段
  - `verified | unverified | unavailable`
- `incremental_value`
  - `fact_id`
  - `novel | covered`
  - 被比对集合
  - 确定性展示文本及核验状态
- `evidence_quality`
  - 只允许离散等级或后端已计算值
  - 理由优先级
- `limitations[]`
  - 唯一 `fact_id`
  - 稳定错误码
  - 通俗中文说明
  - `required_disclosure`
- `allowed_entities[]`
- `allowed_numbers[]`
- `forbidden_claim_types[]`
- `base_reason`
  - `headline`
  - `relevance`
  - `incremental_value`
  - `evidence_note`
  - `limitation`

事实包只能由后端确定性编译器生成。模型不得接收不必要的 PMID、DOI、作者、期刊、题名或原始长全文；不得把未核验字段包装成已核验事实。

## 四、无模型基础理由

设计独立、纯函数化、可单测的基础理由编译器。理由固定覆盖：

1. 为什么与当前主题相关；
2. 是否为当前集合之外的增量候选；
3. 能确定的研究类型或证据特点；
4. 当前必须告知用户的限制。

必须至少处理：高匹配新增、相关但已覆盖、仅题名可用、无摘要、探索推荐、已确认 Intent、信息不足等情况。中文应通俗，不直接向用户堆叠内部评分或英文错误码。

## 五、模型润色输入输出

小模型只接收事实包和基础理由，不从零生成理由。输出必须是固定 JSON：

```json
{
  "schema_version": "recommendation-reason-output-v1",
  "headline": {"text": "...", "fact_ids": ["..."]},
  "relevance": {"text": "...", "fact_ids": ["..."]},
  "incremental_value": {"text": "...", "fact_ids": ["..."]},
  "limitation": {"text": "...", "fact_ids": ["..."]}
}
```

每个段落必须引用事实包中真实存在的 `fact_ids`。模型不得参与候选选择、评分、排序、覆盖判断，也不得修改事实包。

固定系统提示词必须要求：

- 只能使用事实包内容；
- 不新增疾病、药物、研究设计、数字或结论；
- 不生成疗效、安全性、因果关系、统计显著性或临床建议；
- 不输出 PMID、DOI、作者、期刊或题名；
- 必须保留 `required_disclosure=true` 的限制；
- 信息不足时保留基础理由；
- 只返回指定 JSON。

## 六、输出校验

润色结果展示前必须依次通过：

1. JSON Schema；
2. 必填段落和字数；
3. 所有 `fact_ids` 均存在；
4. 强制限制项全部被引用并表达；
5. 不含允许列表外的新实体；
6. 不含允许列表外的新数字；
7. 不含“证明、证实、显著改善、显著降低、应当采用、必然、因果”等越界表达；
8. 不含疗效、安全性、因果或未核验比较结论；
9. 不泄漏禁止身份字段；
10. 不存在空泛、重复或与基础理由矛盾的内容。

任一校验失败，整次润色作废并保留基础理由；记录稳定原因码，不向用户展示内部堆栈。

## 七、运行与持久化状态

候选必须保留基础理由和润色理由的独立快照，建议至少支持：

- `base_reason_json`
- `reason_fact_packet_json`
- `polished_reason_json`
- `display_reason_source = base | polished`
- `narration_status = not_requested | pending | running | completed | fallback_timeout | fallback_unavailable | fallback_rejected`
- `narration_model`
- `narration_error_code`
- `polished_at`

根据现有模型和迁移风格确定最小数据库变更，不把这些状态塞进无法查询或无法约束的临时前端状态。旧推荐记录升级后必须能继续读取，并默认展示原有确定性理由。

推荐运行应在候选及基础理由持久化后立即变为 active。随后异步润色前 `candidate_count` 篇（默认最多 10 篇），并发最多 2，单篇硬超时 8～12 秒，总任务有界。相同事实包指纹不得重复消耗模型。

应用重启后，pending/running 润色应可恢复或安全降级；不得无限停留在 running。并发重复 worker 不得覆盖较新的结果或破坏用户接受/忽略决定。

## 八、前端交互

仅修改文献推荐页专属组件、Composable/API 类型及测试：

- 基础理由生成后立即展示推荐列表；
- 润色中使用非阻塞提示：“推荐已生成，正在优化表述”；
- 润色完成后局部刷新理由，不清空列表、不重置分页和用户决定；
- 超时/不可用/拒绝时显示基础理由，可用中性提示“当前展示可核验的标准理由”；
- 不使用全页骨架屏或“正在生成”按钮锁住已激活结果；
- 推荐历史和刷新页面后仍能恢复相同状态；
- 保持探索推荐页内编辑检索式的现有功能。

## 九、验收标准

### AC-RR-01 无模型可用

Given 未配置任何语言模型，When 生成推荐，Then 候选、排序和通俗基础理由完整生成并持久化，运行变为 active。

### AC-RR-02 先激活后润色

Given 模型响应被人为阻塞，When 候选处理完成，Then 推荐列表先变为可读 active，模型阻塞不得延长主生成状态。

### AC-RR-03 严格事实包

Given 真实候选元数据，When 编译事实包，Then 每条可展示事实都有唯一 fact_id、来源、核验状态，且未核验信息不能进入已核验事实。

### AC-RR-04 基础理由覆盖

Given 新增、已覆盖、无摘要、探索和 Intent 场景，When 生成基础理由，Then 四段式理由与限制准确、通俗且不产生新医学事实。

### AC-RR-05 模型输入最小化

Given 润色任务，When 构造模型输入，Then 不包含不必要的 PMID、DOI、作者、期刊、题名或全文，只含严格事实包和基础理由。

### AC-RR-06 引用事实原子

Given 模型返回润色 JSON，When 校验，Then每段引用的 fact_ids 必须存在，否则整次输出被拒绝并保留基础理由。

### AC-RR-07 防新增实体和数字

Given 模型加入未允许的药物、疾病或数字，When 校验，Then 输出被拒绝且不会写入展示理由。

### AC-RR-08 防医学越界

Given 模型生成疗效、安全性、因果、统计显著性或临床建议，When 校验，Then 输出被拒绝并记录稳定原因码。

### AC-RR-09 强制限制保留

Given 事实包含 required_disclosure，When 模型省略限制，Then 输出被拒绝，基础理由仍显示该限制。

### AC-RR-10 超时与不可用降级

Given 模型超时、连接失败或 JSON 不合法，When 润色运行，Then推荐保持 active、基础理由可读，状态进入对应 fallback，页面无红色核心功能错误。

### AC-RR-11 成功原子替换

Given 合规润色输出，When 保存完成，Then 只更新该候选润色字段和展示来源，不改变候选身份、排序、评分、覆盖状态或用户决定。

### AC-RR-12 并发与幂等

Given 两个独立 session/worker 同时润色相同候选，When 完成，Then 相同事实包不重复生效，旧 worker 不覆盖更新版本，且状态最终一致。

### AC-RR-13 重启恢复

Given pending/running 润色在进程退出时中断，When 应用恢复，Then任务可恢复或按超时规则降级，不无限 running，活动推荐继续可读。

### AC-RR-14 前端非阻塞体验

Given 推荐已 active 且润色 pending/running，When 用户查看、分页、接受或忽略候选，Then所有操作正常；润色完成仅局部刷新理由，页面刷新后状态仍一致。

## 十、测试和门禁

建立 AC-RR-01～14 到真实测试的追踪表。测试必须覆盖：

- 事实包与基础理由纯函数单测；
- 校验器的允许与拒绝矩阵；
- 两个独立数据库 session 的并发/幂等；
- 调度器超时、模型不可用和重启恢复；
- API 契约、持久化和历史读取；
- Vue 页面“先展示、后台润色、局部刷新、失败回退”的行为测试。

完成前必须运行并报告：

1. `tests/modules/recommendation` 下全部测试；
2. 与 recommendation 直接相关的 literature_search/literature_scoring 回归；
3. Ruff；
4. 前端推荐页及推荐 API/Composable 测试；
5. 前端 typecheck（若被无关既有错误阻塞，必须列出具体文件并证明本次目标文件无新增类型错误）；
6. 新临时数据库上的 upgrade → downgrade → upgrade；
7. 临时数据库 Alembic check；
8. `git diff --check`，并区分本轮问题与既有无关问题。

只有 AC-RR-01～14 每项都有真实测试映射且通过，才能声明完成。

## 十一、最终报告

最终报告必须包含：

- AC-RR-01～14 的测试文件与测试名称映射；
- 修改文件；
- 数据契约和状态机摘要；
- 迁移 revision；
- 全部验证命令和结果；
- 是否写入或升级正式数据库；
- 模型不可用时的实际降级行为；
- 仍存在的结构性限制。
