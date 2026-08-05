# Mini-RAG 基线（R2-WP09）实验说明

本实验验证 `app/rag/` 的 Markdown 笔记检索基线：**索引 Obsidian 笔记 → 检索 → 溯源 → 重启后加载索引**。
全部能力为本地 Python API（`NotesRAG`），无 HTTP 端点；Embedding 本地优先（Ollama），dummy 兜底，**不调用云端**。

> 本目录下的 `notes/` 放实验用样例笔记；`demo.py` 是手工验证脚本；构建出的索引写入 `data/notes_index/`
> （已被 `.gitignore` 忽略，不入库）。

## 架构与融合点

| 融合点 | 在本基线的体现 |
| --- | --- |
| 本地 embedding 优先 | `app/rag/embeddings.py`：`EMBEDDING_PROVIDER=ollama\|dummy`，默认 `dummy`；Ollama 不可达时抛 `EmbeddingError` 而非自动切云端 |
| 可解释引用（反幻觉） | 检索结果返回 `RetrievalResult(text, source_path, heading, score)`，调用方可直接打开 `source_path` 溯源 |
| 元数据边界 | **FAISS 只存向量 + vector_id**；`chunk_id/heading/text/source_path` 存独立 `metadata.json`，检索按 vector_id 回查（详见 `app/rag/faiss_store.py`） |

```text
experiments/minirag/
├── README.md                 # 本说明
├── demo.py                   # 手工验证脚本：索引→3 问→溯源→重载
└── notes/                    # Obsidian 笔记样例（即本实验的笔记目录）
    ├── EGFR 耐药机制研究.md
    └── 系统评价与Meta分析.md
```

## 环境准备

- 后端 Python：`/f/software/programme/Anaconda/envs/med-research-ai/python.exe`（Python 3.12）
- Windows 下 `PYTHONPATH` 被全局设为 Hermes venv，**所有 python 命令前必须加 `env PYTHONPATH=""`**
- 依赖：`app/rag` 使用 `faiss-cpu`、`numpy`、`httpx`（均已在项目 `pyproject.toml`）
- Embedding 配置（`.env`，默认即 dummy，无需改动即可离线跑通）：

```dotenv
# Mini-RAG 笔记检索（R2-WP09）：本地优先，ollama 失败时用 dummy 兜底，不切换云端
EMBEDDING_PROVIDER=dummy          # 开发用哈希向量（非语义向量）
# EMBEDDING_PROVIDER=ollama       # 本地语义向量，需本机 Ollama 已拉取模型
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIMENSION=384
```

> `dummy` 返回**确定性哈希向量**，仅用于开发与离线测试，**非语义向量**：它只保证同一文本映射同一向量，不携带语义。

## 手工验证步骤

以下命令全部在仓库根目录执行（均使用后端 conda 环境的 python；`--provider` 默认 `dummy`）。

### 1. 索引 Obsidian 笔记

`demo.py` 会把 `notes/` 目录下所有 `.md` 文件按标题切片（超长标题段回退固定长度切片），
逐块嵌入后建立 FAISS L2 索引，并保存到 `data/notes_index/`：

```powershell
$env:PYTHONPATH=''
& '/f/software/programme/Anaconda/envs/med-research-ai/python.exe' experiments\minirag\demo.py --provider dummy
```

预期输出包含索引统计与 3 个问题的检索结果：

```text
[索引] 文档数=2, 分块数=N, 维度=16, 索引目录=data\notes_index
[Q1] T790M 突变与 EGFR 耐药有什么关系？
  - 命中: <text 摘要>
    source: experiments\minirag\notes\EGFR 耐药机制研究.md  (# 一代与二代 EGFR-TKI 的耐药机制)   score=...
[Q2] 奥希替尼的耐药机制有哪些？
  - 命中: ...
[Q3] 系统评价中如何衡量异质性？
  - 命中: ...
[保存] 索引已保存到 data\notes_index
[重载] 索引加载成功（dimension=16, embedding_model=dummy-hash）
[重载] 再次检索通过，来源路径与首次一致
```

### 2. 提出 3 个问题并验证来源路径

脚本内置 3 个问题（T790M 耐药 / 奥希替尼耐药 / 异质性），打印每条命中的 `source_path` 与 `heading`。
**手工核对**：打开 `source_path` 指向的笔记文件，确认命中的 `heading` 段落确实包含相关表述——
即"来源路径可显示、可追溯"。如需换问题，用 `--questions`（分号分隔）：

```powershell
$env:PYTHONPATH=''
& '/f/software/programme/Anaconda/envs/med-research-ai/python.exe' experiments\minirag\demo.py --questions '什么是旁路激活？; meta-analysis 是什么？'
```

> dummy 向量无语义，命中内容可能偏离提问；这只验证**引用可溯源**。要获得语义相关命中，
> 使用 Ollama 提供方（见下）。真实命中文本是否相关、能否支持回答，永远以人工核验为准。

### 3. 重启后加载索引

`demo.py` 每次都会在**新进程**内加载 `data/notes_index/` 的索引后再检索（第 5 步），
等价于"服务重启后从磁盘加载"。可用 `--skip-index` 跳过重建、只验证加载：

```powershell
$env:PYTHONPATH=''
& '/f/software/programme/Anaconda/envs/med-research-ai/python.exe' experiments\minirag\demo.py --skip-index --provider dummy
```

预期：`[加载] 索引加载成功` 且检索正常返回来源。若更换了 embedding 模型/维度，加载会抛
`EmbeddingDimensionMismatchError` 并提示**重建索引**（不静默截断，见 `faiss_store.load`）。

### 4. 使用 Ollama（本地语义向量，可选）

若本机已运行 Ollama 并拉取了 `nomic-embed-text`，把 `.env` 中 `EMBEDDING_PROVIDER` 改为
`ollama` 后，用同一命令索引与检索即可获得语义相关命中；`EMBEDDING_DIMENSION` 保持 384
（Ollama 客户端会校验响应维度与声明一致，不匹配报错提示重建）。Ollama 不可达时抛
`EmbeddingError`，不会自动切换到云端。

## 索引文件结构（`data/notes_index/`）

| 文件 | 内容 |
| --- | --- |
| `manifest.json` | 格式版本 + embedding 模型名 + 向量维度（加载前先校验） |
| `vectors.npy` | 全部向量（FAISS 只存向量，**不存元数据**） |
| `vector_ids.npy` | 与 `vectors.npy` 对齐的 vector_id 数组 |
| `metadata.json` | 按 vector_id 的元数据记录（chunk_id/document_id/heading/text/source_path），检索后回查 |

## 设计边界与已知限制

- **无 HTTP 端点**：本基线是 Python API（`NotesRAG.index / search / save_index / load_index`），
  挂 REST 端点属于后续工作包。
- **dummy 非语义向量**：仅开发/测试用，检索命中不代表语义相关，来源可溯源仍成立。
- **仅处理 Markdown**：当前索引 `notes_dir.glob("*.md")` 顶层文件，不递归子目录。
- **不做高级多向量与 Agent**（R2-WP09 显式限制）。
- **元数据独立存储**：FAISS 文件缺失元数据时必须重建；`faiss_store` 对损坏/维度变化显式报错并提示重建。

## 自动化测试

核心逻辑均有单元测试覆盖（切片、dummy 中英文向量、FAISS round-trip、Top-K 边界、来源映射、
维度变化重建提示）：

```powershell
$env:PYTHONPATH=''
& '/f/software/programme/Anaconda/envs/med-research-ai/python.exe' -m pytest tests\rag\ -q
```

> 本实验所有命令与示例代码均未在本会话运行，标注【未实测】；以实际执行为准。

## 下一步

R2-WP09 收尾后，下一任务是 R2-WP10（融合点延伸，如把 `NotesRAG` 挂到 API 或接入问答），
本实验不执行。
