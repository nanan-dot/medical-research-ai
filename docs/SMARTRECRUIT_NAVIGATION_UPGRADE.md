# SmartRecruit 检索经验迁移 第一轮

## 范围

升级 `/api/v1/document-navigation/search`：采用内容指纹索引复用、扩大召回候选、本地 CrossEncoder 重排及同文档重复证据去重。沿用 FAISS、BM25、RRF 和既有数据库，不增加 ES、Milvus 或 MongoDB。选定论文的 PaperQA2 问答不在本轮范围。

## 请求流程

读取启用知识源下已解析且已索引资料 → 建立当前范围的块与页码映射 → BM25 或 FAISS 加 BM25 混合召回 → 可选本地重排 → 同文档相同正文去重 → 截取最终结果。

候选量由导航专属硬上限控制：向量、词法、融合与重排候选分别读取 `NAVIGATION_DENSE_TOP_K`、`NAVIGATION_SPARSE_TOP_K`、`NAVIGATION_FUSION_TOP_K` 和 `NAVIGATION_RERANK_CANDIDATE_TOP_K`。服务不再通过 `max(...)` 偷偷扩大配置；请求超过候选预算时返回 `candidate_budget.status=limited`。

独立 BM25 与语义检索失败后的 BM25 降级均先执行 `NAVIGATION_SPARSE_TOP_K`，再执行重排候选上限；BM25 响应中的 `candidate_budget` 会反映这条路径的实际 Sparse 候选上限。混合检索分别执行 Dense、Sparse、Fusion 与 Rerank 上限，不用最终候选量反向放大任一召回分支。

## 配置和调用

现有 Python 环境及模型依赖沿用 `pyproject.toml`。如缺少本地模型依赖，安装项目 `local-models` 可选依赖组。运行时不下载模型。

使用以下环境变量启用已放置好的本地重排模型，随后按项目原方式重启服务：

```powershell
$env:NAVIGATION_RERANK_ENABLED = 'true'
$env:NAVIGATION_RERANK_MODEL_DIR = 'D:\AI_project\rag_medicine\data\models\bge-reranker-base'
$env:NAVIGATION_RERANK_INITIALIZATION_TIMEOUT_SECONDS = '60'
$env:NAVIGATION_RERANK_TIMEOUT_SECONDS = '30'
$env:NAVIGATION_DENSE_TOP_K = '30'
$env:NAVIGATION_SPARSE_TOP_K = '30'
$env:NAVIGATION_FUSION_TOP_K = '40'
$env:NAVIGATION_RERANK_CANDIDATE_TOP_K = '40'
$env:PYTHONPATH = ''
& 'F:\software\programme\Anaconda\envs\med-research-ai\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
$body = @{ query = 'PD-1'; limit = 10; indexed_only = $true } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/v1/document-navigation/search' -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))
```

真实语义召回继续依赖原有 Ollama Embedding 配置；未启用时使用 BM25。重排可独立作用于 BM25 候选。导航开关不受全局 `RERANK_ENABLED` 影响。2026-09-19 已在本机 `.env` 启用 `NAVIGATION_RERANK_ENABLED`，并配置项目内完整的 `data/models/bge-reranker-base`。

## 接口兼容

原有字段保留。响应新增 `rerank_reason_code`、`candidate_budget`、`effective_indexed_only` 和 `trace_id`。每条结果新增 `condition_matches`，将 `metadata_match`、`metadata_mismatch`、`text_mention` 与 `not_assessed` 分开；正文年份不再验证出版年份，RCT 正文命中也不再升级为事实。模型未配置、失败或得分异常时保留检索顺序。分数不代表医学结论正确概率。

导航 Trace 结构化记录 `rerank_status` 与 `rerank_reason_code`，混合检索分别记录原始 `dense_candidates`、`sparse_candidates`、RRF 融合顺序和重排顺序。默认策略仍不持久化查询和正文，并把候选中的路径收敛为文件名，避免保存本机绝对路径。

## 索引边界

缓存仅在当前进程内，默认最多 4 个快照、总计 4096 个块；超出单次预算的索引只用于当前请求。指纹包含数据目录、向量服务地址、模型名、维度和全部块的正文与身份。范围、正文或模型名变化后重新建立快照。已缓存但不再符合当前范围的旧快照不会被当前请求使用，之后按 LRU 淘汰。

缓存不落盘，不保证跨进程或重启复用。同一快照的检索通过锁串行保护。并发首次请求可能重复构建，发布后复用同一快照。当前预算按块数限制，不是字节级内存限制。

重排模型按目录在进程内缓存。首次初始化在工作线程内完成资产校验、SHA-256 内容指纹和模型加载；加载前后的文件签名必须一致，才会发布带该内容指纹的 scorer。切换到不同目录会建立新缓存；同目录原地替换目前不会热失效，受支持的失效与重载方式仍是重启服务。资产若在首次加载过程中变化，本次初始化会失败并保留原检索顺序。

## 去重和引用

仅去掉同一文档中空白规范化后完全相同的正文，不删除不同文档的相同文本，不把同一文档不同证据强制合成一条。返回的正文、文档身份、页码和章节来自原检索结果，重排只改变顺序。

## 已知限制与后续

初始化等待与推理等待使用两个独立边界：`NAVIGATION_RERANK_INITIALIZATION_TIMEOUT_SECONDS` 只限制请求等待首次校验、指纹和加载；`NAVIGATION_RERANK_TIMEOUT_SECONDS` 只限制请求等待推理。`asyncio.wait_for` 超时不会强制终止底层同步线程；后台工作结束前，进程内单飞锁使后续请求返回 `model_busy`，避免继续排队。本轮没有建立医学专家标注集，没有声称准确率、召回率或延迟提升。

后续可分别迭代：父子块及精确页内锚点、显式跨轮检索条件、持久化增量索引、真实标注集与消融评估。每项应独立验收。

## 文件

- `app/modules/document_navigation/index_cache.py`：内容寻址的有界内存索引缓存。
- `app/modules/document_navigation/ranking.py`：串行保护的本地模型与重排适配。
- `app/modules/document_navigation/service.py`：检索编排、硬预算、重排与 Trace 接入。
- `app/modules/document_navigation/corpus.py`：分块、证据映射和结果去重。
- `app/modules/document_navigation/conditions.py`：元数据约束与正文提及的保守判定。
- `app/modules/document_navigation/budget.py`：导航专属候选预算。
- `app/modules/document_navigation/trace.py`：复用全局脱敏策略的导航审计轨迹。
- `app/modules/document_navigation/schema.py`：兼容新增条件、预算、重排原因与 Trace 字段。
- `app/core/config.py`：导航独立开关与各阶段 Top-K。
- `tests/modules/document_navigation/test_retrieval_upgrade.py`：离线缓存、重排及接口回归。

## 验证命令

2026-09-19 本次检索升级修复最终结果：用户指定的导航、RAG 与配置组合回归共 156 项通过，耗时 37.90 秒；本次范围 Ruff 通过；mypy 检查 13 个相关源文件通过。新增回归覆盖 BM25 独立/降级 Sparse Top-K、初始化事件循环响应、初始化超时后的单飞、加载期间资产变更、同目录缓存显式失效、混合检索各阶段顺序、结构化重排 Trace 以及初始化/推理独立配置边界。

真实本地模型检查已完成：后端安装项目锁定的 `torch 2.7.1`、`transformers 4.57.6` 和 `sentence-transformers 5.1.2`；模型目录包含完整 CrossEncoder 分类头。离线 CPU 首次加载及三候选推理耗时约 21.2 秒，相关 RCT 文本得分 `0.999616`，无关文本得分 `0.000321`。棱镜检查修复了公共 5 秒阈值导致的假回退；导航独立阈值为 30 秒，40 条短候选真实业务重排耗时 `5.422` 秒并返回 `applied`。主动超时与单飞锁保证超时请求及时返回，模型占用期间的新请求返回 `model_busy`。这证明模型可加载并能完成排序，不代表医学检索质量评测结论。

SmartRecruit 教学仓库中的同名资产经张量清单检查缺少分类头，直接交给 CrossEncoder 会随机初始化打分层，因此运行配置采用项目内已有的完整同名模型。复制出的原始资产未被运行配置引用，并带有 `DO_NOT_USE.txt` 标记。

```powershell
$env:PYTHONPATH = ''
& 'F:\software\programme\Anaconda\envs\med-research-ai\python.exe' -m pytest tests/modules/document_navigation tests/rag tests/test_retrieval_config.py tests/test_rag_trace_config.py tests/test_grounded_rag_config.py -q
& 'F:\software\programme\Anaconda\envs\med-research-ai\python.exe' -m ruff check app/modules/document_navigation app/rag/transformers_reranker.py tests/modules/document_navigation app/core/config.py
& 'F:\software\programme\Anaconda\envs\med-research-ai\python.exe' -m mypy app/modules/document_navigation app/core/config.py
```
