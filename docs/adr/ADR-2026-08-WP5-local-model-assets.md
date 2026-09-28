# ADR：WP5/WP7 本地真实模型资产

日期：2026-08-25

## 决策

- CrossEncoder 为 `BAAI/bge-reranker-base`，固定 revision `2cfc18c9415c912f9d8155881c133215df768a70`，已下载到项目目录并通过 safetensors 完整性读取；只从该本地目录以 CPU 加载，绝不在 import 或请求路径下载。
- 实际 Shadow reranker 统一使用该 CrossEncoder；模型不可用时回退 baseline，不使用其他模型重排。
- PaperQA2 继续作为唯一默认核心与主编排；生成模型由既有用户 provider 配置决定，不将特定厂商或模型嵌入 RAG。
- 新下载的 reranker 文件只能放入 `data/models/bge-reranker-base/`。HF 环境变量只在下载进程临时设置。
- 默认仍是 PaperQA2；真实本地模型先仅在 Shadow 使用。
- 导航重排首次初始化在线程池内完成校验、SHA-256 内容指纹和模型加载；加载前后文件签名必须一致，模型版本才可发布。初始化等待和推理等待使用独立超时配置，超时不表示底层同步线程被终止。

## 依据与资源

- BAAI 官方 Hugging Face 模型卡：MIT；中英文 reranker；主 `model.safetensors` 约 1.11GB。该卡列出 CMedQAv1/2 reranking 评测，但不等同于本项目医学效果。
- 机器实测：RTX 5060 Ti 约 8GB 显存、当前空闲约 5.4GB；可用物理内存约 2.5GB；D 盘可用约 413GB。Reranker 不与 8B generator 同时常驻。
- 已在项目 `.venv` 安装并核验：`torch==2.7.1+cpu`、`transformers==4.57.6`、`sentence-transformers==5.1.2`；`huggingface-hub==0.36.2`、`tokenizers==0.22.2` 为固定 Transformers 依赖解析结果，`pip check` 通过。PyTorch 为 BSD-3-Clause，Transformers / Sentence-Transformers 为 Apache-2.0（包元数据/官方项目）。
- CPU build 下 `torch.cuda.is_available()==False`；本轮只做 CPU 基准，不擅自替换 CUDA wheel。
- 完整性与本机 CPU 实测：`model.safetensors` 为 1,112,206,140 字节、202 个 tensor 键；公开合成样例中 sotorasib 直接证据得分 `0.9484944`，adagrasib 背景为 `0.2236650`。首次评分 `8,189.3ms`；warm 样本 `n=3` 为 42.4/43.6/44.5ms，P50 43.6ms、P95 44.5ms。它们不是生产 SLA 或医学效果结论。

## 风险与回滚

- 首次加载产生冷启动、显存/内存压力；配置中保持 `RERANK_ENABLED=false` 与 `GROUNDED_RAG_ENABLED=false`。
- 模型加载、推理或超时失败必须回退原检索/PaperQA2；BGE 分数仅用于相关度排序，不判断医学正确性或证据等级。
- 进程内模型缓存按目录复用。同目录原地替换尚不支持热失效，必须重启服务以清空缓存并重新绑定内容指纹；该限制保留到热重载策略完成并发与资产一致性验证。
- 回滚：关闭上述 feature flags，删除 `data/models/bge-reranker-base/`，从 `.venv` 卸载上述项目级包；不涉及系统级状态。
