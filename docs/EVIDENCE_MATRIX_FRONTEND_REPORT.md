# 证据矩阵真实前端接入：实现报告

## 已实现

- 移除原有 `prototypePapers`、`prototypeFields` 与浏览器内存备注；
- 新增真实 API 适配器 `frontend/src/api/evidenceMatrices.ts`；
- 页面可读取、切换和新建证据矩阵；
- 页面可显示真实文档、字段、单元格、矩阵版本与来源状态；
- 单元格失焦时会调用真实编辑 API；
- 可调用真实的“重新生成”接口，且界面明确说明人工修改不会被重生成覆盖；
- 详情栏显示单元格状态和后端返回的 PMID/DOI/定位信息；没有来源时明确说明不能作为已生成证据。

## 组件边界

- `EvidenceMatrixView.vue`：数据加载、矩阵选择、创建与业务编排；
- `EvidenceMatrixTable.vue`：表格渲染、局部编辑和单元格选择事件；
- `EvidenceMatrixInspector.vue`：来源、状态与人工修订说明；
- `evidenceMatrices.ts`：HTTP 契约和类型。

## 仍未接入的后端能力

后端已有但本轮尚未补上前端操作：

- 向矩阵加入/移除文档；
- 新增/删除字段；
- 修改矩阵名称、描述、状态；
- CSV/Markdown 导出。

这些能力没有被伪装为已完成。

## 实际验证

已运行并通过：

```text
npm run typecheck
npm test -- --run
npm run build
```

结果：类型检查通过；Vitest `21` 个测试文件、`33` 项测试通过；生产构建成功。

测试输出中仍有既有的 Vue Router 与 `/api/v1/health` 测试环境警告，但测试命令退出码为 `0`；本轮未新增这些警告。
