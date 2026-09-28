# SmartRecruit 重排接入棱镜审查

## Generated Pipeline

1. 运行真实性：贯通 `.env`、Settings、模型加载、重排服务与响应状态，寻找模型可运行但业务未采用结果的断点。
2. 证据与身份：构造完整、缺分类头和内容不同的模型资产，检查预检、版本与 Trace 是否忠实描述实际资产。
3. 边界与并发：检查空候选、无效分数、超时、候选上限、冷启动与串行模型锁的回退行为。
4. 发布闭环：核对配置、依赖、测试隔离、运行文档与回滚边界，攻击所有“已生效”结论。

## Pass 1：运行真实性

原始 scorer 能对三条文本给出合理分数，但 `rank_candidates` 使用公共 `RerankerService` 的默认 5 秒阈值。真实调用耗时 6.136 秒，最终状态是 `fallback/inference_error`，排序结果被丢弃。这证明“模型能推理”不等于“业务重排已生效”。修复后导航使用独立 `NAVIGATION_RERANK_TIMEOUT_SECONDS=30`，超时返回独立原因码。

真实 40 候选测试耗时 5.422 秒，状态 `applied`；相关候选从第 18 位升至第 1 位。

## Pass 2：证据与身份

SmartRecruit 教学资产有 199 个基础编码器张量，没有分类头；医学项目完整资产有 202 个张量，并包含 `classifier.dense` 与 `classifier.out_proj` 权重。原预检只检查文件名，会接受教学资产并由 CrossEncoder 随机初始化打分头。修复后加载前检查 safetensors 张量键，缺分类头返回 `model_unavailable`。

原模型版本硬编码为固定 revision，任意完整目录都会写出相同身份。修复后版本来自配置、分词器和权重文件的 SHA-256 内容指纹，当前为 `BAAI/bge-reranker-base@sha256:0a8cd06400489e16`，并写入 RetrievalTrace。

## Pass 3：边界与并发

空候选返回 `no_candidates`，未配置模型返回 `model_unavailable`，NaN、长度错误和推理异常返回 `inference_error`，超过阈值返回 `timeout`。候选数受导航专属硬预算限制。模型调用由进程内锁串行化，避免同一 CrossEncoder 并发进入非线程安全路径。

导航层现使用 `asyncio.wait_for` 主动限制请求等待时间。底层同步推理无法被 Python 线程强制终止，因此真实 scorer 增加非阻塞单飞锁：超时后的一个后台推理可以继续完成，但后续请求立即返回 `model_busy`，不会排队堆积线程。真实状态转换测试为：首次调用 `0.014` 秒返回 `timeout`，紧接调用 `0.001` 秒返回 `model_busy`，模型释放后恢复 `applied`。

仍保留一个底层限制：如果 Torch 推理永久挂死，模型会持续处于 busy，需要重启工作进程；当前方案把影响限制为一个推理线程和明确降级，不会无界堆积任务。

## Pass 4：发布闭环

本机 `.env` 已启用导航重排并配置 30 秒阈值；Settings 新进程读取验证通过。固定版本依赖安装完成，`pip check` 无冲突。测试夹具显式关闭本机重排配置，自动化测试不会因开发机 `.env` 产生漂移。当前没有运行中的 Uvicorn 进程，下次启动自动加载配置。

最终验证：相关测试 147 项通过；本次范围 Ruff、mypy 通过；`pip check` 无依赖冲突；真实离线 40 候选业务重排通过。

## Adversarial Pass

- **撤回**：最初“真实模型已生效”的结论不成立；当时只验证了 scorer，业务层仍因 5 秒阈值回退。
- **收紧**：30 秒阈值仅在当前 CPU、40 条短文本样本上得到支持。更长分块、冷缓存和并发排队可能超过阈值。
- **收紧**：分类头存在不能单独证明权重训练正确；真实排序 smoke test提供额外证据，但仍不能替代医学标注集。
- **新增**：硬编码模型 revision 会破坏 Trace 的可重放性，内容指纹是审查后新增的必要修复。
- **共同假设**：测试查询具有明显词面相关性。医学同义词、否定、时间约束和证据等级上的质量仍未知。

## Final Findings

**Conservation law**：只有最终业务响应状态、候选顺序和 Trace 都引用同一份经校验的模型资产，才能声称重排生效；单独的模型加载成功不足以支持该结论。

| 位置 | 问题 | 严重度 | 结果 |
| --- | --- | --- | --- |
| `document_navigation/ranking.py` | 5 秒阈值造成正常 CPU 推理假回退 | 高 | 已修复 |
| `rag/transformers_reranker.py` | 缺分类头资产可被当作重排模型 | 高 | 已修复 |
| `rag/transformers_reranker.py` | 模型版本硬编码，Trace 身份失真 | 中 | 已修复 |
| `document_navigation/ranking.py` | 超时请求持续阻塞，后续任务可能堆积 | 高 | 已用主动超时和单飞保护修复 |
| Torch 同步推理 | 永久挂死时线程无法强制终止 | 低 | 影响已限制为单线程，恢复需重启 worker |
| 医学质量评测 | 合成 smoke test 不能证明临床检索质量 | 中 | 待标注集评测 |

**Deepest finding**：最大风险不是模型加载失败，而是模型成功打分后被业务阈值静默丢弃；只有贯穿 scorer 到最终响应的真实性测试才暴露这一点。
