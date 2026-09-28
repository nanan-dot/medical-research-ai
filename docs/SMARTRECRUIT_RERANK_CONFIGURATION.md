# SmartRecruit 重排模型接入记录

## 生效配置

本机 `.env` 已启用：

```dotenv
NAVIGATION_RERANK_ENABLED=true
NAVIGATION_RERANK_MODEL_DIR=D:\AI_project\rag_medicine\data\models\bge-reranker-base
NAVIGATION_RERANK_INITIALIZATION_TIMEOUT_SECONDS=60
NAVIGATION_RERANK_TIMEOUT_SECONDS=30
NAVIGATION_DENSE_TOP_K=30
NAVIGATION_SPARSE_TOP_K=30
NAVIGATION_FUSION_TOP_K=40
NAVIGATION_RERANK_CANDIDATE_TOP_K=40
```

运行环境安装项目 `local-models` 锁定版本：`torch 2.7.1`、`transformers 4.57.6`、`sentence-transformers 5.1.2`、`protobuf 6.33.6`。

## 资产核验

SmartRecruit 使用 `CrossEncoder` 加载名为 `bge-reranker-base` 的本地目录。教学仓库中的这份资产缺少分类头张量，直接运行会让分类头随机初始化。医学项目原有同名资产包含 `classifier.dense` 和 `classifier.out_proj` 四个分类头张量，因此运行配置指向完整资产。

## 真实推理

在 `HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1` 下执行三候选 CPU 推理：

- RCT 肝癌相关文本：`0.999616`
- 糖尿病无关文本：`0.000321`
- 肝癌免疫治疗综述：`0.172434`
- 排名第一项正确；首次加载及推理约 `21.239` 秒。

该检查验证模型资产、依赖和调用链可运行。医学检索准确率、召回率和临床质量仍需标注集评测。

棱镜检查进一步发现原有公共重排器的 5 秒阈值会把正常 CPU 推理标记为回退。导航现使用独立的 30 秒阈值，并返回独立的 `timeout` 原因码。40 条短候选的真实业务重排耗时 `5.422` 秒，状态为 `applied`，相关候选从第 18 位升至第 1 位。Trace 中的模型版本改为内容指纹 `BAAI/bge-reranker-base@sha256:0a8cd06400489e16`。

首次资产校验、SHA-256 指纹和模型加载在线程池内执行，受 60 秒初始化等待边界约束；加载前后文件签名变化时不发布 scorer。推理另受 30 秒等待边界约束。两处 `asyncio.wait_for` 都只限制请求等待，不会强制终止底层同步线程；后台初始化或推理结束前，进程内单飞锁让同时到达的请求返回 `model_busy`，避免线程排队。此前真实测试记录中的 `timeout=0.014s`、`model_busy=0.001s` 仅描述当次环境，不作为 SLA。

进程缓存以模型目录为键并绑定首次成功加载的内容指纹。切换目录会加载新资产；同目录原地替换不会自动热失效，必须重启服务后重新校验、计算指纹并加载。在同目录热重载策略通过独立并发与资产一致性验证前，这一限制保持不变。
