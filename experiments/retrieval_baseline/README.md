# R2-WP10 检索基线对比

此实验复用 WP09 的 Markdown 样例、切片器、Dummy embedding 与 FAISS 元数据回查，分别运行 `vector`、`bm25` 与 `hybrid`。问题和相关 `chunk_id` 是可审查的人工标注；输出保存每一路的原始分数、排名、RRF 贡献和聚合指标，而非以主观感觉判断。

中文分词不依赖 jieba：连续中文产生确定性二元组，拉丁字母/数字医学词以完整小写 token 保留。因此 `EGFR`、`NCT04209660` 不会被拆开，`奥希替尼` 可由二元组召回。

在仓库根目录执行：

```powershell
$env:PYTHONPATH=''
& F:\software\programme\Anaconda\envs\med-research-ai\python.exe experiments\retrieval_baseline\run_baseline.py --output data\retrieval_baseline.json
```

输出 JSON 含各策略的 `mean_recall_at_k` 和 `mean_mrr`，以及每个问题的完整结果；同目录还生成 `.retrieval.jsonl` 追踪各路 Top-K 和融合结果。Dummy embedding 仅用于离线可复现的流程验证，不能作为语义检索质量结论；需要语义对比时，应使用同一已验证的本地 Ollama embedding 重新构建索引并执行同一人工标注问题集。
