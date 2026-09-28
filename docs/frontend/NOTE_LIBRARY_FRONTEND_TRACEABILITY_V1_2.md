# 笔记库前端 V1.2 验收追溯

日期：2026-09-01。生产页面仅使用 `/api/v1/note-library`；测试数据均为明确的合成 fixture。

| 验收项 | 自动化证据 | 结果 |
|---|---|---|
| AC-NLF-01 路由接入 | `router.test.ts` — `AC-NLF-01 reaches...`; `AppSidebar.test.ts` | PASS |
| AC-NLF-02 版式层级 | `NoteLibraryWorkspace.test.ts` 三列断言；`note-library.spec.ts` 1774×887 当前实现的回归快照 | PARTIAL（未执行冻结参考图像的像素级 diff） |
| AC-NLF-03 快捷视图 | `noteLibrary.test.ts` view/count 参数；Playwright quick counts | PASS |
| AC-NLF-04 搜索一致性 | `useNoteLibrary.ts` AbortController + sequence；Playwright 防抖请求断言 | PASS |
| AC-NLF-05 筛选 | `noteLibrary.test.ts` repeated tags/research parameters | PASS |
| AC-NLF-06 分页边界 | `noteLibrary.test.ts` page/page_size 20/50/100 contract | PASS |
| AC-NLF-07 列表信息 | Playwright 合成 fixture 的标题、摘要、标签、来源/研究状态 | PASS |
| AC-NLF-08 选择与深链 | Playwright `note_id` 选择和详情恢复 | PASS |
| AC-NLF-09 收藏与元数据 | `noteLibrary.test.ts` metadata CAS payload | PASS |
| AC-NLF-10 同页新建编辑 | Playwright 同页编辑对话框；生产 `newNote()` | PASS |
| AC-NLF-11 草稿自动保存 | Playwright draft GET/PUT；`aria-live` 保存状态与离页保护 | PASS |
| AC-NLF-12 正式保存与幂等 | `noteLibrary.test.ts` expected versions/idempotency；Playwright commit | PASS |
| AC-NLF-13 冲突安全 | 409 分支保留本地内容，提供重载、复制与对比；API CAS 测试 | PASS |
| AC-NLF-14 历史与恢复 | `noteLibrary.test.ts` history/restore；Playwright 分页历史展示与版本内容查看 | PASS |
| AC-NLF-15 来源能力降级 | Playwright revoked source 显示“来源已撤销”；按钮按 capability 控制 | PASS |
| AC-NLF-16 归档生命周期 | `noteLibrary.test.ts` archive/unarchive endpoint contract | PASS |
| AC-NLF-17 加载/空态/错误 | `NoteLibraryWorkspace.test.ts` — `keeps a failed list request recoverable` | PASS |
| AC-NLF-18 键盘与无障碍 | Playwright Enter/Escape；ArrowUp/Down handler；语义按钮与 `aria-live` | PASS |
| AC-NLF-19 响应式 | Playwright 390×844 预览→列表返回；CSS 1220/900 断点 | PASS |
| AC-NLF-20 端到端闭环 | `e2e/note-library.spec.ts` 搜索→选择→编辑→保存→历史→移动端 | PASS |

## 门禁结果

- Typecheck：PASS。
- 笔记库目标 Vitest：15 tests PASS。
- 前端全量 Vitest：88 files / 266 tests PASS。
- Production build：PASS（仅既有 PDF chunk 体积警告）。
- Playwright：1 PASS；1774×887 当前实现回归快照 PASS。该快照用于后续视觉回归，不能替代与冻结参考图的像素级比较。
- ESLint：目标文件 0 errors。
- `git diff --check`：PASS；仅工作区既有 LF/CRLF 提示。

## 能力边界

- 后端未修改；未创建迁移；未升级、降级或写入正式数据库。
- actor scope 由 adapter 固定为 `local`，界面不宣称多租户鉴权。
- `ai_suggestions_unavailable` 不产生 AI 操作按钮。
- 原文定位仅在来源 capability 明确允许时才可呈现；撤销或缺失来源使用降级状态。
