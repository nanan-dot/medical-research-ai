# 统一科研对话

生产入口：`/api/v1/unified-conversations`；前端直达：`/research-chat`。

先执行 `u1chat20260904` 迁移。`GET /capabilities` 返回 `migration_ready`，未升级时所有写入接口明确返回升级提示，不会自动迁移。

请求支持 `auto`、`general`、`evidence_only`。`general` 使用已保存的默认模型；文献事实走 PaperQA2；混合回答使用独立 sections；外部来源仅在 `allow_web_search=true` 且提供 `web_query` 时调用 PubMed。通用回答没有引用，历史消息保留来源身份，不能变成证据。

每个请求需要 `request_id`。同会话同编号同内容会重放已保存响应，不同内容冲突；数据库唯一活动锁防止并发生成重复助手消息。取消、断线、超时会保存失败终态。知识缺口只在真实证据不足且没有检索/系统故障时记录，并按本地单用户、范围、问题去重，可删除。

上线前必须备份现有 SQLite，再运行 Alembic 迁移；真实模型和 PubMed 联调需另行授权。全库召回和跨文献综合尚未宣称可用。
