# A2 自由选区与共享锚点验收追踪

状态：A2 功能已实现；2026-09-01 Full Prism 独立审计为**部分通过**。存活的范围内 P2 已修复，但旋转、真实医学复杂布局黄金集和不受并行 A3 迁移影响的全量门禁仍缺少实测证据。

## 契约与验收映射

| ID | Given / When / Then | 验证位置 | 状态 |
|---|---|---|---|
| A2-01 | UTF-16 首尾范围 / 重建 / 保留代理对、组合字符及医学符号，非法边界拒绝 | `test_selection_ranges.py` | 7 passed |
| A2-02 | 反向、跨 item/行/栏/页选区 / 按 A1 排序 / 原文连续且不混栏 | `test_reconstruction.py`、浏览器跨页用例 | 通过 |
| A2-03 | 重复原文 / 保存 / 不同范围使用不同身份 | reconstruction、API | 通过 |
| A2-04 | 伪造 quote、空白、越界或缺失 item / 创建 / 拒绝且无资产写入 | reconstruction、API | 通过 |
| A2-05 | 错误或未发布 A0/A1、文件换版 / 创建 / 409 且不自动取最新 | API | 通过 |
| A2-06 | 未授权源或跨文档 anchor / 使用 / 拒绝 | API | 通过 |
| A2-07 | 相同幂等键 / 重试 / 同请求返回原结果，不同请求 409 | API、并发用例 | 通过 |
| A2-08 | 业务失败 / 原子事务 / anchor、fragments、coverage、资产全部回滚 | API 故障注入 | 通过 |
| A2-09 | 保存原文锚点 / 重开 / quote、上下文、范围、坐标可追溯 | API、真实 PDF.js 浏览器用例 | 通过 |
| A2-10 | TextLayer 对齐失败、端点歧义 / 选择 / 禁用精确保存并显示原因 | `pdfSelection.test.ts` | 通过 |
| A2-11 | 正反向、容器/br 端点 / 捕获 / 相同稳定 item 与 UTF-16 范围 | `pdfSelection.test.ts` | 通过 |
| A2-12 | 缩放/旋转/刷新 / 定位 / 精确范围或显式几何/页级降级 | `PdfAnnotationReader.test.ts`、真实浏览器放大用例 | 缩放/刷新通过；90/180/270 度旋转【未实测】 |
| A2-13 | 工具栏获焦与编辑冻结 / 切换文档 / 保留草稿、失效选区清除且旧请求不覆盖 | `DocumentAnnotationWorkspace.test.ts`、组合式防陈旧响应 | 通过 |
| A2-14 | 高亮/批注/笔记引用同一 anchor / 修改业务内容 / 原文不可变 | API、真实浏览器用例 | 通过 |

## 本轮证据

- 后端定向回归：`35 passed`（包含 A0/A1 坐标契约、A1 重发布顺序，以及 A2 选择、资产、事务与并发）。
- 后端完整回归：`1019 passed, 13 skipped`；唯一警告来自 Starlette 对其 `httpx` 测试客户端的弃用提示。
- 前端：`vue-tsc` 通过；A2 定向 Vitest `6 passed`。
- 浏览器：真实 PDF.js + 隔离 SQLite + A0/A1 数据，`2 passed`；覆盖笔记/批注共享 anchor、刷新和 140% 缩放后精确重定位，以及跨两页原生选择。
- 视觉检查：`frontend/test-results/a2-selection-restored.png` 中的黄色高亮与第一页 TextItem 字符范围一致。

## 实现边界与运行说明

API 以 A0 revision、A1 segmentation revision、文件哈希和 TextItem 的 UTF-16 偏移作为写入前置条件。服务端重建 quote 并比对浏览器 quote；不接受客户端任意文本作为锚点。`document_source_anchors`、fragment 和 segment coverage 不提供更新接口；批注与阅读笔记仅引用它们。

新迁移为 `b31a2c4d5e60_shared_source_selections`。A1 同时升为 `a1-layout-2`：修正 A0 PDF `[x0,y0,x1,y1]` bbox 被误当 `[x,y,width,height]` 的问题，并在发布新分割版本前先将旧 current 版本标记为 stale，避免唯一索引冲突。

真实医学复杂布局黄金集、A3 跨版本重定位、A4 窗口化及翻译生成不在本轮实现；不会以合成夹具冒充医学质量验收。

## Full Prism 对抗审计（2026-09-01）

### 范围与隔离

本轮只修改以下 A2 白名单文件：

- `frontend/src/utils/pdfSelection.ts`
- `frontend/src/utils/pdfSelection.test.ts`
- `tests/modules/document_anchor/test_selection_ranges.py`
- `docs/A2_SELECTION_ANCHOR_TRACEABILITY.md`

`document_relocation`、A3 迁移、A3 测试和 A3 文档均未修改。审计期间 `PdfAnnotationReader.vue` 与 `PdfAnnotationReader.test.ts` 被并行任务继续修改；本轮未写入这两个文件，最终门禁按结束时快照重跑。A2 资产服务当前读取 A3 的 `AssetAnchorLink`，因此后端集成结果不能被描述为完全脱离 A3 工作区的独立构建。

### Generated Pipeline

**Pass 1 — 版本化身份与端点守恒账本。** 从原始 DOM `Selection/Range`、PDF.js `TextLayer` 映射、A0 TextItem、A1 rank、`SourceAnchorDescriptor`、后端重建、不可变 Anchor、刷新回放逐跳建立账本。为每一跳构造正向、反向、同 item、跨 item、跨页和重复 quote 的最小实例；记录 document、file hash、anchor/segmentation revision、page、item、UTF-16 半开端点、方向、quote 与矩形是否被转换、验证或丢失。随后反构造一个只缺少中间 TextItem 的回放，验证系统是否仍声称 exact。

**Pass 2 — Unicode 与连接规则对抗矩阵。** 继承 Pass 1 的身份账本，把每个文本端点替换为 BMP、代理对、ZWJ 医疗 emoji、组合附加符、variation selector、NBSP、软连字符，并组合跨 TextItem、跨页与反向拖选。为每格同时计算 JavaScript UTF-16 code unit 长度和 Python 切片边界，构造落在代理对中间的反例；再检查浏览器 quote、后端重建 quote、规范化比较、quote hash 与持久化原文是否保持敏感数字和符号。

**Pass 3 — 状态、事务、并发与授权状态机。** 继承前两轮的端点和 Unicode 结论，构造 `ready/review_required/stale` A0/A1 状态、错误 revision、文件换版、同键同请求、同键异请求、并发创建、业务写入失败和失效知识源。沿 API→Service→数据库 savepoint 绘制可见状态，检查是否存在 Anchor 已写但资产失败、重复资产、错误文档 Anchor 复用或未经知识源可用性检查的读取；把单机本地授权与多用户 IDOR 分开，不凭不存在的用户模型推断跨用户漏洞。

**Pass 4 — 几何与证据强度反例。** 继承前三轮已确认的版本与状态约束，构造缩放、HiDPI、90/180/270 度旋转、滚动容器、双栏、跨页和页面窗口卸载模型。区分 viewport 坐标、DOM client rect、页面归一化矩形和 TextItem 字符范围，尝试让部分映射、旧几何或未加载页面冒充 exact。最后逐项审计测试是否为真实后端、真实 PDF.js、合成 PDF、route mock 或纯单元夹具，并用当前命令结果反查本报告中的数量和“已实测”措辞。

### Pipeline 顺序执行结果

#### Pass 1：端到端守恒账本

保存链路的主身份为 `(document_id, file_hash, anchor_revision_id, segmentation_revision_id, ordered(page, item, [start_utf16,end_utf16)))`。前端 `Range` 已由浏览器规范化拖选方向，映射层逐项核对 `source_array_index/item_index/text`；后端重新加载固定 A0/A1、按 rank 排序、以 Python UTF-16 专用函数重建 quote，并用包含 revision、范围和 quote hash 的指纹去重。API 与真实浏览器用例证明保存、刷新和跨页顺序保持。反例 `fragment=[item 0..1]`、回放映射只有 item 0 时，旧 `locateFragments` 仍生成 item 0 的矩形并使调用方显示“按 TextItem 字符范围精确定位”，破坏 exact 的完整性语义。

#### Pass 2：Unicode 对抗矩阵

新增参数化矩阵实际覆盖 `α ≤ 5`、`A😀B`、`👩‍⚕️`、`e + U+0301`、`✌ + U+FE0F`、NBSP 和软连字符，逐例验证 UTF-16 长度与整段无损回放；既有用例继续验证代理对中点拒绝、组合字符独立边界、反向跨页及数字/比较符伪造 quote 拒绝。结果为 `21 passed`。矩阵没有发现 JavaScript code unit 与 Python code point 混用；后端 `slice_utf16` 明确在代理对中点失败。字素簇边界不是当前持久化不变量：组合符、ZWJ 与 variation selector 可在合法 Unicode scalar 边界切分，这是当前设计允许但尚未版本化为字素策略的行为。

#### Pass 3：状态、并发、权限与原子性

定向 API 基线覆盖错误 A0/A1 revision、文件换版、失效知识源、跨文档 Anchor、同键重试、同键冲突、并发 get-or-create 和故障注入回滚，结果 `25 passed`（含纯函数用例）。`load_context` 在写事务内以 Document 行更新建立 SQLite 写栅栏，并刷新 A0/A1 状态；业务资产与 Anchor 位于同一 savepoint。当前产品授权边界是本地知识源 `enabled`，仓库没有可用于构造“跨用户”的 actor principal，因此不能把“跨用户 IDOR 已验证”写成事实；已验证的是失效源和跨文档拒绝。A2 资产层当前依赖并行 A3 的链接模型，这属于隔离证据限制，不在本轮反向修改 A3。

#### Pass 4：几何与证据审计

缩放与 HiDPI 的守恒点是 DOM client rect 除以当前 `.pdf-page` 边界；devicePixelRatio 仅影响 canvas backing store，不进入归一化矩形。真实 Playwright 使用合成的两页 PDF、真实 PDF.js、隔离 SQLite 和真实 FastAPI，完成选择→保存→刷新→字符范围定位及 140% 缩放，`2 passed`。窗口卸载由并行 A4 代码影响，本轮只审计 A2 回放的失败降级。当前没有 90/180/270 度真实 PDF 或单元用例，也没有双栏医学黄金 PDF；原报告关于“旋转坐标契约单测通过”的表述与代码不符，已改为【未实测】。证据分类不能把合成 PDF 称为真实医学黄金集。

### 额外 Adversarial Pass（Pipeline 设计完成后新增）

对“端点身份全链路守恒”的反证条件是：固定 revision 下任一中间 item 缺失、端点越界或 quote 改变仍返回 exact。部分映射反例确实推翻旧实现，修复后要求 item 数量、首尾索引和每项非空范围全部成立。对“Unicode 混用”的反证条件是代理对中点被 Python 接受或完整 ZWJ 序列回放变化；实际测试未出现，因此撤回该候选 bug。对“事务结构缺陷”的反证条件是故障注入后残留 Anchor/资产；现有集成测试没有残留，故不把可疑的 nested transaction 写法升级为缺陷。对“IDOR”的反证是系统没有用户主体；因此只保留跨文档与知识源可用性结论。所有 pass 共同误设“报告中的历史通过数量仍代表当前快照”，迁移 head 漂移和旋转测试缺失证明该假设错误。

### Retracted claims

- 撤回“部分映射问题是窗口化造成的结构缺陷”：它是 `locateFragments` 内可局部修复的完整性 bug，不需要重构阅读器。
- 撤回“当前代码存在跨用户 IDOR”：仓库当前没有用户主体；只能证明跨文档与失效知识源拒绝。
- 撤回“90/180/270 度旋转已有坐标契约单测”：当前 A2 测试没有该证据，标记【未实测】。
- 撤回“真实 PDF 浏览器用例等于真实医学复杂布局验收”：本轮是实际 PDF 文件与真实栈，但 PDF 内容为合成双页夹具。
- 撤回第一次残缺映射实验的假绿：jsdom 默认没有 client rect，返回 `null` 是无几何副作用；注入可见 rect 后才得到稳定 RED。

### Survived findings

| 文件/行 | 破坏行为 | 严重度 | 性质 | 证据与处置 |
|---|---|---|---|---|
| `frontend/src/utils/pdfSelection.ts`，`locateFragments` | 多 item fragment 仅映射部分 TextItem 时仍返回矩形，上层误报 exact，高亮与持久化范围不一致 | P2 | 可修复 | RED：`1 failed, 3 passed`，收到 item 0 矩形而非 `null`；修复为验证完整 item 数量、首尾索引及非空端点；GREEN：A2 前端定向 `13 passed` |
| `docs/A2_SELECTION_ANCHOR_TRACEABILITY.md`，A2-12/历史证据 | 把不存在的旋转测试写成已通过，可能导致在 90/180/270 未验证时错误放行 | P2 | 可修复（证据） | `rg` 仅找到 rotation=0 夹具；已改为 90/180/270【未实测】，不再宣称门禁通过 |

### Deepest finding

最深层问题不是 offset 算错，而是“exact”曾由“产生了任意可见矩形”隐式定义。持久化身份要求完整有序范围，但回放层只验证了局部可画性；窗口化或部分映射因此能把信息缺失伪装成精确成功。对抗轮把 conservation law 收紧为：**只有 document/file/revision 一致，且每个 fragment 的全部 TextItem 与两个 UTF-16 半开端点均可重建时，UI 才能声称 exact；几何只能后备，不能证明文本身份。**

### RED→GREEN 与命令结果

- RED：`npm run test -- --run src/utils/pdfSelection.test.ts` → `1 failed, 3 passed`；残缺 multi-item fragment 返回了局部矩形。
- GREEN：同一测试与 A2 组件联合运行 → `13 passed`。
- Unicode/重建：`pytest test_selection_ranges.py test_reconstruction.py -q` → `21 passed`。
- A2 后端初始定向：`pytest test_selection_ranges.py test_reconstruction.py test_api.py -q` → `25 passed`。
- A0/A1/A2 扩展基线：全量含迁移测试首次为 `125 passed, 1 failed`；失败是 `test_a0_migrations_roundtrip_without_losing_preexisting_data` 硬编码旧 head `c42d3e4f5a61`，当前并行迁移 head 为 `a3f9e8d7c6b5`，属于并行工作区影响，本轮未修改。排除该单一、已证明与 A2 无关的迁移断言后，结束快照为 `133 passed`。
- 本轮较早的 `npm run typecheck` 与 `npm run build` 均通过；Vite 仅报告既有大 chunk 警告。结束快照重跑时，`vue-tsc` 被并行非 A2 文件 `MedicalTranslationPanel.vue:147` 阻断：只读 `alignment` 不能赋给可变数组；本轮未修改该文件，因此结束 typecheck/build 不能标为 A2 完整绿色。
- 隔离真实栈 Playwright：合成 PDF + 真实 PDF.js + 真实 FastAPI + 隔离 SQLite，`2 passed`；默认 4173 被并行任务占用，本轮使用临时 4174 配置，没有终止对方服务。

### 未实测与结论

- 90/180/270 度旋转的真实 PDF.js 选择与刷新回放【未实测】。
- 真实医学双栏、复杂表格、软连字符断词黄金 PDF【未实测】；Unicode 字符本身已做纯函数矩阵。
- 多用户 IDOR【不适用/未实测】：当前本地授权模型没有用户主体。
- 不含并行 A3/A4 工作区变化的全后端回归【未实测】；已有扩展基线明确受迁移 head 漂移影响。

因此本轮不能写“A2 通过棱镜测试”；准确结论为：**A2 Full Prism 部分通过，存活的范围内 P2 已修复，剩余阻塞为旋转/真实医学黄金集证据和并行迁移隔离门禁。**
