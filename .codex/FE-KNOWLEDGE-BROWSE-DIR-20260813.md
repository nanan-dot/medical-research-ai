# 授权目录 Windows 文件夹选择器（FE-KNOWLEDGE-BROWSE-DIR-20260813）

> 本提示词由 Hermes 基于用户设计决策（方案 C：后端浏览端点 + 前端浏览按钮）生成，供 Codex 执行。
> 执行前必须先读仓库规范与现状，再动手。

## 一、任务总览

为知识库的"资料文件夹"创建流程增加 **Windows 原生文件夹选择器**能力：
- 用户在"授权目录"字段不再只能手写路径，可点击"浏览…"按钮弹出系统文件夹选择器
- 选择后真实绝对路径回填到输入框，用户确认后提交

**技术前提（为什么需要后端端点）**：浏览器沙箱无法调用 Windows 原生对话框，`<input type="file" webkitdirectory>` 只返回模糊路径（`C:\fakepath\...`）。本项目的**后端是本地进程**，Python 可弹原生对话框。

## 二、必读文件（执行前按序阅读）

1. `docs/CODE_STANDARDS.md` — 代码生成强制规范 V2.0（42 条，最高规范）
2. `frontend/src/components/knowledge-source/KnowledgeSourceForm.vue` — 主修改对象（授权目录字段 L55-62）
3. `frontend/src/api/knowledgeSources.ts` — API 客户端（加 browse 方法）
4. `app/modules/knowledge_source/router.py` — 后端路由（加 browse 端点）
5. `app/modules/knowledge_source/service.py` 或新建 — 服务层（对话框逻辑）
6. `app/modules/knowledge_source/schema.py` — Pydantic 模型（响应模型）
7. `tests/modules/knowledge_source/test_api.py` — 现有测试（加 browse 测试）

## 三、⚠️ 工作区边界

**当前有未提交文件（其他会话/本功能进行中）——必须保留，不执行 git reset/checkout，不 stash：**
```
M app/modules/knowledge_source/import_service.py（新建知识库导入，已修 source_type）
M app/modules/knowledge_source/router.py
M app/modules/knowledge_source/schema.py
M frontend/src/api/knowledgeSources.ts
M frontend/src/components/knowledge-source/SingleDocumentImportPanel.vue
M frontend/src/components/knowledge-source/KnowledgeSourceManager.vue
M frontend/src/components/knowledge-source/KnowledgeSourceForm.vue
M frontend/src/components/knowledge-source/KnowledgeSourceList.vue
M frontend/src/views/Documents/DocumentsView.vue
M frontend/src/views/KnowledgeBase/KnowledgeBaseView.vue
M frontend/src/components/document/DocumentManager.vue 等
```

**你只允许修改**：
1. `app/modules/knowledge_source/router.py`（加 browse 端点）
2. `app/modules/knowledge_source/service.py` 或新建 `browse_service.py`（对话框逻辑）
3. `app/modules/knowledge_source/schema.py`（响应模型）
4. `frontend/src/api/knowledgeSources.ts`（加 browseDirectory 方法）
5. `frontend/src/components/knowledge-source/KnowledgeSourceForm.vue`（浏览按钮 + 回填）
6. `tests/modules/knowledge_source/test_api.py`（browse 测试）

**禁止触碰**：其他知识库文件（SingleDocumentImportPanel/KnowledgeSourceManager/List）、DocumentManager、路由、后端其他模块。提交时只 add 上述文件，**绝不用 `git add -A`**。

## 四、后端实现（方案 C 核心）

### 4.1 新端点
```
POST /api/v1/knowledge-sources/browse-directory
请求体：无（或空 body）
响应 200：{ "path": "H:\\research\\papers" }
响应 4xx：{ "detail": "当前环境无法弹出目录选择器" }（无桌面会话时）
```

### 4.2 对话框实现（关键约束）

**必须遵守 fastapi-router-py skill：`async def` 处理器不得直接调用阻塞 I/O**——tkinter 的 GUI 主循环是阻塞的，必须放线程池：

```python
# 推荐实现（tkinter，Windows 自带）
def _pick_directory() -> str | None:
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口，只弹选择器
    root.attributes("-topmost", True)  # 置顶，避免被浏览器窗口遮挡
    try:
        return filedialog.askdirectory(title="选择资料文件夹")
    finally:
        root.destroy()

# 端点内
path = await asyncio.to_thread(_pick_directory, ...)
```

**备选实现（PowerShell，更原生）**：
```python
# System.Windows.Forms.FolderBrowserDialog，Windows 专属但体验最原生
# 若用此方案：ps 脚本 + subprocess，同样放线程池
```

**二选一，优先 PowerShell FolderBrowserDialog**（Windows 原生、与资源管理器一致）；tkinter 为兜底（无需额外依赖）。**若两者都因无桌面会话失败 → 返回明确 4xx**，前端提示改用手动输入。

### 4.3 安全与校验
- 用户通过系统对话框选择的路径 = **用户授权**，但仍需校验：路径存在、可访问（`Path.is_dir()`）
- 返回前用 `normalized_path_key` 或类似规范化（与现有知识源一致）
- **不**自动创建知识源（本端点只"选择路径"，创建仍走现有 KnowledgeSourceForm 提交）
- 响应模型：`{ "path": str | None }`（用户取消选择返回 `{ "path": null }`，前端保留原值）

## 五、前端实现

### 5.1 API 客户端（knowledgeSources.ts）
```ts
browseDirectory: () => apiRequest<{ path: string | null }>("/knowledge-sources/browse-directory", { method: "POST" }),
```

### 5.2 KnowledgeSourceForm.vue
- "授权目录"字段（L55-62）改为**输入框 + 浏览按钮**的组合：
  ```
  [输入框 H:\research\papers      ] [浏览…]
  ```
- 点击"浏览…"：调 `browseDirectory()` → 返回非 null 则回填 `form.root_path`；null（用户取消）保持原值；4xx 显示错误提示"当前环境无法弹出目录选择器，请手动输入路径"
- 浏览期间按钮禁用 + 文案"选择中…"（防重复点击）
- 错误显示在字段下方（红色小字），不清空已输入内容
- 按钮样式：描边按钮，与输入框同高，`aria-label="浏览文件夹"`

### 5.3 交互细节
- 浏览按钮触发的是后端弹窗——**提示用户"将弹出系统文件夹选择窗口"**（避免用户以为没反应）
- 键盘可达：Tab 到浏览按钮可激活
- 成功回填后，用户仍可手改（浏览是增强不是替代）

## 六、测试要求

**后端**（`tests/modules/knowledge_source/test_api.py`）：
- browse 端点返回 200 且 path 是字符串（mock 对话框返回固定路径）
- 对话框抛异常/无桌面会话时返回 4xx（mock 抛错）
- 用户取消返回 `{ "path": null }`（mock 返回 None）
- **用 mock 隔离**：不真正弹窗（CI 无 GUI），patch 对话框函数

**前端**（`KnowledgeSourceForm.test.ts` 如存在）：
- 点击"浏览…"调用 browseDirectory
- 成功回填 root_path
- 失败显示错误且保留原值

## 七、验证命令（必须真实运行并报告）

```bash
# 前端
cd /h/AI_project/rag_medicine/frontend
npm run typecheck
npm run test
npm run build

# 后端（项目 Python + 清空 PYTHONPATH）
cd /h/AI_project/rag_medicine
env PYTHONPATH="" /f/software/programme/Anaconda/envs/med-research-ai/python.exe -m pytest tests/modules/knowledge_source/ -q
```

⚠️ 若 Codex 沙箱拒绝 pytest（写临时 SQLite），记录"未运行"并说明，不要声称通过；Hermes 独立重跑。

## 八、最终报告格式

1. 实际修改文件清单
2. 新端点真实请求/响应契约
3. 对话框实现选型（PowerShell vs tkinter）与原因
4. 无桌面会话时的降级行为（4xx → 前端提示手动输入）
5. 实际测试命令与真实结果
6. 已知限制（如仅 Windows 可用、【未实测】项）
