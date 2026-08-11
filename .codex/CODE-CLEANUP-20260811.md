# 素问·全项目代码治理执行提示词（CODE-CLEANUP-20260811）

> 本提示词由 Hermes 生成，供 Codex 执行。执行前必须先读仓库规范与现状，再动手。
> 目标：死代码清理 + 注释规范化 + 工具检查，**零回归**。

## 一、任务总览

对 rag_medicine 全项目（FastAPI 后端 + Vue3 前端）执行一次**保守的代码治理**：
1. 删除无用的死代码与被注释掉的代码（**仅限确认无引用的**）
2. 规范化代码格式（遵守 CODE_STANDARDS.md）
3. 增加/修正注释（**只写设计意图，删复述行为的废话注释**）
4. 用工具检查（ruff/mypy/eslint）并修复**新引入**的问题

**铁律：不允许任何功能行为变更，不允许删除任何有引用的代码。全部验证必须真实运行。**

## 二、必读文件（执行前按序阅读）

1. `docs/CODE_STANDARDS.md` — 代码生成强制规范 V2.0（42 条，最高规范，必须服从）
2. `pyproject.toml` — 后端依赖与工具配置
3. `frontend/package.json` — 前端依赖与脚本

## 三、⚠️ 工作区边界（最高优先级，违反即失败）

当前有 **13 个未提交文件是另一个会话的进行中工作，你绝对禁止触碰**：

```
frontend/src/api/conversations.ts
frontend/src/api/documents.ts
frontend/src/api/paperAnalysis.ts
frontend/src/views/Chat/ChatView.test.ts
frontend/src/views/Chat/ChatView.vue
frontend/src/views/Documents/DocumentDetailView.vue
frontend/src/views/PaperAnalysis/PaperAnalysisView.test.ts
frontend/src/views/PaperAnalysis/PaperAnalysisView.vue
frontend/src/components/paper/CurrentPaperSelector.vue
frontend/src/components/paper/PaperAnalysisSection.vue
frontend/src/components/paper/ReadingAnnotationSection.vue
frontend/src/components/paper/SinglePaperConversationSection.vue
frontend/src/composables/usePaperResearchWorkflow.ts
```

- 这 13 个文件**不允许读取后修改、不允许格式化、不允许删除任何内容**
- 清理范围 = **除上述 13 个文件外的全部已提交代码**
- 提交时只 add 你改过的文件，绝不用 `git add -A`

## 四、执行步骤

### 步骤 1：工具基线（只读，不修改）
```bash
cd /h/AI_project/rag_medicine
env PYTHONPATH="" /f/software/programme/Anaconda/envs/med-research-ai/python.exe -m ruff check app/ tests/ 2>&1 | tail -5
env PYTHONPATH="" /f/software/programme/Anaconda/envs/med-research-ai/python.exe -m mypy app/ 2>&1 | tail -5
cd frontend && npx eslint src/ 2>&1 | tail -5
```
记录基线问题数，输出到交付说明。**基线问题不要求全修**（既有遗留），只修你在清理过程中新引入的。

### 步骤 2：死代码与注释代码清理（保守）
按模块分批（每批不超过 3 个文件），每个候选删除前：
1. `grep -rn "名字" app/ tests/ frontend/src/` 确认无引用（import/调用/模板引用/路由）
2. 被注释掉的代码：**纯死代码删除**；**带设计说明的注释保留**（改写为正常注释）
3. 未使用的 import/变量删除（eslint/ruff 会提示）
4. **每批删除后跑对应模块测试**

### 步骤 3：注释规范化
- 复杂逻辑（>10 行、状态机、边界处理）补**中文设计意图注释**（为什么这样设计、权衡、坑）
- 公共函数/组件补 Docstring/JSDoc：一句话职责 + 参数 + 返回 + 异常
- **删除**复述行为的注释（如 `# 遍历列表`、`// 设置值`）
- 简单自解释代码不加注释

### 步骤 4：格式规范化
- 后端：`ruff format` 仅对你改过的文件（不全局跑，避免污染其他会话文件）
- 前端：`npx prettier --write` 仅对你改过的文件
- **禁止格式化 13 个边界文件**

## 五、验收标准（必须全部真实运行并报告输出）

```bash
# 后端全量
cd /h/AI_project/rag_medicine
env PYTHONPATH="" /f/software/programme/Anaconda/envs/med-research-ai/python.exe -m pytest tests/ -q 2>&1 | tail -3
# 前端
cd frontend && npm run typecheck 2>&1 | tail -3
npm run test 2>&1 | tail -5
npm run build 2>&1 | tail -3
```

- **pytest 必须 538 passed（或更多，不许少）**——删除代码不得破坏任何测试
- **typecheck 0 错误**（基线无错误，不许引入新错误）
- **前端测试全过**（基线 32 files / 58 tests）
- **build 成功**
- 若删除某代码导致测试失败：**恢复该删除**（说明为什么不能删），继续下一批

## 六、交付说明（完成后输出）

1. 改动文件清单（含每个文件的删除/修改统计）
2. 删除的死代码/注释代码清单（文件:行 + 为什么确认无用）
3. 补充的注释清单（文件:行 + 注释了什么设计意图）
4. 工具基线 vs 清理后的问题数对比
5. 验证命令真实输出（pytest/typecheck/test/build）
6. 边界文件确认未被触碰
7. 已知限制与【未实测】项

## 七、禁止事项

- ❌ 不修改任何功能行为、不重命名、不重构逻辑
- ❌ 不触碰 13 个边界文件
- ❌ 不用 `git add -A`（只 add 自己改的文件）
- ❌ 不提交、不推送（只改工作区，提交由 Hermes 决定）
- ❌ 不全局格式化（只格式化自己改的文件）
- ❌ 不新增依赖、不修改配置
