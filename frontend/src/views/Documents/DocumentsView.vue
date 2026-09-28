Exit code: 0
Wall time: 2 seconds
Output:
<script setup lang="ts">
import { useTemplateRef } from "vue";

import DocumentManager from "../../components/document/DocumentManager.vue";

const manager = useTemplateRef<InstanceType<typeof DocumentManager>>("manager");
</script>

<template>
  <main class="documents-page" data-design-version="library-reference-v2">
    <header class="documents-heading">
      <div><h1>资料库</h1><p>管理进入研究体系的资料，并提供检索、问答与分析能力</p></div>
      <div class="heading-actions"><button class="manage-button" type="button" @click="manager?.manageSources()">管理资料来源</button><button class="import-button" type="button" @click="manager?.openImport()">导入资料</button></div>
    </header>
    <DocumentManager ref="manager" />
  </main>
</template>

<style scoped>
.documents-page { width:calc(100% - 48px); margin:0 auto; padding:12px 0 48px; }

.documents-heading { display:flex; align-items:center; justify-content:space-between; gap:16px; min-height:68px; margin:0 0 10px; }

.documents-heading h1 { margin:0; color:var(--text-primary); font-size:28px; line-height:36px; letter-spacing:-.02em; }

.documents-heading p { margin:4px 0 0; color:var(--text-muted); font-size:14px; line-height:22px; }
.heading-actions { display:flex; flex:0 0 auto; gap:8px; }.heading-actions button { min-height:40px; border-radius:4px; padding:0 14px; font:inherit; font-size:14px; font-weight:700; cursor:pointer; }.manage-button { border:1px solid var(--border-subtle); background:var(--surface); color:var(--text-primary); }.import-button { border:1px solid var(--color-primary); background:var(--color-primary); color:#fff; }.heading-actions button:focus-visible { outline:2px solid var(--color-primary); outline-offset:2px; }

@media (max-width: 700px) {
  .documents-page { width:calc(100% - 32px); padding-top:16px; }.documents-heading { align-items:flex-start; min-height:0; }.heading-actions { gap:6px; }.heading-actions button { min-height:44px; padding:0 10px; font-size:13px; }
}
</style>

<style scoped>
/* 资料库局部令牌：保留其他路由的现有设计。 */
.documents-page {
  --text-primary: #14203e;
  --text-muted: #617294;
  --color-primary: #0055ff;
  --border-subtle: #e5ebf5;
  --surface: #ffffff;
  --elevated: #f8faff;
  padding-bottom: 16px;
  font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}
.heading-actions { gap: 14px; }
.heading-actions button { border-radius: 8px; min-height: 44px; padding: 0 22px; }
.import-button::before { content: "+"; margin-right: 12px; font-size: 22px; font-weight: 400; }
.documents-page :deep(.document-library) { padding-bottom: 0; }
.documents-page :deep(.workbench) { gap: 20px; border: 0; background: transparent; box-shadow: none; overflow: visible; align-items: start; }
.documents-page :deep(.source-nav),
.documents-page :deep(.document-pane) { border: 1px solid var(--border-subtle); border-radius: 12px; background: var(--surface); }
.documents-page :deep(.document-pane) { padding: 0 12px; }
.documents-page :deep(.pane-heading) { min-height: 46px; padding: 0 10px; border: 0; }
.documents-page :deep(.pane-heading h2) { font-size: 14px; font-weight: 600; }
.documents-page :deep(.context-mark) { display: none; }
.documents-page :deep(.document-filters) { background: var(--surface); padding: 0 10px 14px; border: 0; }
.documents-page :deep(.search-input) { border-radius: 6px; }
.documents-page :deep(.filter-row) { gap: 12px; margin-top: 10px; }
.documents-page :deep(.filter-control) { border-radius: 6px; min-height: 32px; }
.documents-page :deep(.document-table td) { height: 56px; padding-top: 6px; padding-bottom: 6px; }
.documents-page :deep(.document-main) { width: 100%; }
.documents-page :deep(.copy strong) { font-size: 14px; font-weight: 500; }
.documents-page :deep(.health b) { width: fit-content; padding: 3px 12px; border-radius: 20px; }
.documents-page :deep(.health b::before) { content: none; }
.documents-page :deep(.health-success b) { background: #e7f8ee; color: #11854a; }
.documents-page :deep(.health-info b) { background: #edf3ff; color: #0055ff; }
.documents-page :deep(.health-warning b) { background: #fff2e5; color: #ad5800; }
.documents-page :deep(.pagination) { min-height: 46px; padding: 6px 10px; }
.documents-page :deep(.file-icon) { border-radius: 6px; font-size: 9px; }
@media(max-width:1023px) { .documents-page :deep(.workbench) { gap: 0; } }
@media(max-width:767px) {
  .documents-page :deep(.document-pane) { padding: 0 4px; }
  .documents-page :deep(.document-table td) { height: auto; padding-top: 0; padding-bottom: 0; }
  .heading-actions button { padding: 0 10px; }
}
</style>
