# 知识库页面重构追踪表

## 规格—现状—实现—测试

| AC | 规格要求 | 现状审计 | 实现位置 | 验证 |
| --- | --- | --- | --- | --- |
| AC-01 | 1536px 参考布局、240px 侧栏与响应式 | 现有侧栏为 216px，页面为旧卡片布局 | `AppSidebar.vue`、知识库组件 | 视觉截图 + 组件测试 |
| AC-02 | Summary、问题提醒和来源列表使用真实聚合/分页 API | 仅调用旧 list API | `knowledgeSources.ts`、`useKnowledgeSources.ts` | API mock 行为测试 |
| AC-03 | 搜索、筛选、排序、分页同步 URL 且避免竞态 | 未实现 | `KnowledgeBaseView.vue`、composable | 组件测试 |
| AC-04 | 置顶、自动同步失败回滚；同步防重 | 未实现 | `useKnowledgeSourceActions.ts` | 组件测试 |
| AC-05 | 查看文档/问题文档携带正确 query | 旧参数为 `sourceId` | 列表行与 View | 路由断言 |
| AC-06 | 添加、删除确认、菜单只展示后端真实能力 | 旧抽屉不完整 | Dialog / Row | 组件测试 |
| AC-07 | 可访问性与键盘闭环 | 旧开关和删除确认不完整 | 各交互组件 | 组件测试 + 手工浏览器检查 |
| AC-08 | 六视口截图、叠图、差异图 | 未执行 | `docs/frontend/rebuild-artifacts/` | 浏览器验收 |

## API 能力矩阵（审计时）

| 能力 | API | 前端策略 |
| --- | --- | --- |
| 摘要 | `GET /knowledge-sources/summary` | LIVE |
| 分页查询 | `GET /knowledge-sources/page` | LIVE |
| 新建/更新/删除 | `POST/PATCH/DELETE /knowledge-sources` | LIVE |
| 同步任务 | `POST /{id}/sync` | LIVE，按任务已受理展示 |
| 打开目录 | `POST /{id}/open-directory` | LIVE，错误透明展示 |
| 重命名、置顶、自动同步 | `PATCH /{id}` | LIVE |
