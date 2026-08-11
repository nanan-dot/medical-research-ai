<script setup lang="ts">
import { computed, onMounted, shallowRef, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { documentsApi, type BatchIndexResult, type DocumentRecord } from "../../api/documents";
import { useDocuments } from "../../composables/useDocuments";
import { useDocumentUpload } from "../../composables/useDocumentUpload";
import { useKnowledgeSources } from "../../composables/useKnowledgeSources";
import DocumentFilters from "./DocumentFilters.vue";
import DocumentTable from "./DocumentTable.vue";
import DocumentUploadPanel from "./DocumentUploadPanel.vue";

const route = useRoute(); const router = useRouter();
const { documents, filters, total, loading, error, pageNumber, hasPrevious, hasNext, load, applyFilters, retryParse, retryIndex, deleteIndex, previousPage, nextPage } = useDocuments();
const { sources, load: loadSources } = useKnowledgeSources();
const { uploading, error: uploadError, uploadedFilename, uploadedDocument, upload } = useDocumentUpload();
const selectedIds = shallowRef<number[]>([]); const selectedDocument = shallowRef<DocumentRecord | null>(null); const batchResult = shallowRef<BatchIndexResult | null>(null); const batchError = shallowRef<string | null>(null); const parseError = shallowRef<string | null>(null);
const sourceId = computed(() => { const value = route?.query?.sourceId; const parsed = typeof value === "string" ? Number(value) : NaN; return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null; });
const sourceNames = computed<Record<number,string>>(() => Object.fromEntries(sources.value.map((source) => [source.id, source.name])));
const currentSource = computed(() => sources.value.find((source) => source.id === sourceId.value) ?? null);
const canBatchIndex = computed(() => selectedIds.value.length > 0 && !loading.value);
const requestError = computed(() => error.value ?? batchError.value ?? uploadError.value ?? parseError.value);
function selectSource(id:number|null):void{void router.push({path:"/documents",query:id?{sourceId:String(id)}:{}})}
function toggleSelect(id:number,selected:boolean):void{selectedIds.value=selected?[...new Set([...selectedIds.value,id])]:selectedIds.value.filter((item)=>item!==id)}
async function batchIndex():Promise<void>{if(!canBatchIndex.value)return;batchError.value=null;try{batchResult.value=await documentsApi.batchIndex(selectedIds.value);selectedIds.value=[];await load()}catch(cause){batchError.value=cause instanceof Error?cause.message:"批量建立索引失败"}}
async function uploadPdf(file:File):Promise<void>{
  if (!await upload(file)) return;
  await load();
  const document = uploadedDocument.value;
  if (!document) return;
  parseError.value = null;
  // 上传成功即启动服务端解析；解析错误保留在列表中并可由“开始解析/重试解析”恢复。
  void documentsApi.parse(document.id).then(load).catch((cause: unknown) => {
    parseError.value = cause instanceof Error ? cause.message : "自动解析启动失败";
    void load();
  });
}
watch(sourceId, (nextSourceId) => { void applyFilters({ ...filters, knowledgeSourceId: nextSourceId }); }, { immediate: true });
onMounted(()=>{void loadSources()})
</script>
<template><section class="workspace"><aside class="scope panel"><h2>资料范围</h2><button :class="{active:sourceId===null}" @click="selectSource(null)">全部文档 <b>{{ total }}</b></button><RouterLink v-if="sources.length===0" to="/sources">去知识库添加资料文件夹 →</RouterLink><button v-for="source in sources" :key="source.id" :class="{active:source.id===sourceId}" @click="selectSource(source.id)">{{ source.name }} <b>{{ source.stats?.total_files ?? 0 }}</b></button></aside><section class="panel list"><DocumentFilters :filters="filters" :disabled="loading" @change="applyFilters"/><div class="list-header"><span>{{ currentSource ? `文档库 / ${currentSource.name}` : '全部文档' }}</span><DocumentUploadPanel :uploading="uploading" :error-message="uploadError" :uploaded-filename="uploadedFilename" @upload="uploadPdf"/></div><div v-if="selectedIds.length" class="bulk">已选择 {{ selectedIds.length }} 篇 <button :disabled="!canBatchIndex" @click="batchIndex">批量建立索引</button></div><p v-if="batchResult" class="result">批量结果：{{ batchResult.succeeded }} 成功，{{ batchResult.failed }} 失败。</p><p v-if="requestError" class="error" role="alert">{{ requestError }} <button @click="load">重试</button></p><DocumentTable :documents="documents" :disabled="loading" :selected-ids="selectedIds" :selected-document-id="selectedDocument?.id ?? null" :source-names="sourceNames" @toggle-select="toggleSelect" @select-document="selectedDocument=$event" @retry-parse="retryParse" @retry-index="retryIndex" @delete-index="deleteIndex"/><footer class="pagination"><button :disabled="loading||!hasPrevious" @click="previousPage">上一页</button><span>第 {{ pageNumber }} 页 · 共 {{ total }} 篇</span><button :disabled="loading||!hasNext" @click="nextPage">下一页</button></footer></section><aside class="detail panel"><template v-if="selectedDocument"><h2>{{ selectedDocument.original_filename ?? selectedDocument.file_path }}</h2><p>{{ sourceNames[selectedDocument.knowledge_source_id] ?? '未提供来源名称' }}</p><dl><div><dt>类型</dt><dd>{{ selectedDocument.media_type ?? '未提供' }}</dd></div><div><dt>文件大小</dt><dd>{{ selectedDocument.file_size }} bytes</dd></div><div><dt>解析</dt><dd>{{ selectedDocument.parse_status }}</dd></div><div><dt>索引</dt><dd>{{ selectedDocument.index_status }}</dd></div></dl><p v-if="selectedDocument.error_message" class="detail-error">{{ selectedDocument.error_message }}</p><RouterLink :to="`/documents/${selectedDocument.id}`">打开文档详情 →</RouterLink></template><template v-else><h2>当前范围</h2><p>选择一篇文档，查看真实处理状态、错误信息和元数据。</p><dl><div><dt>文档总数</dt><dd>{{ total }}</dd></div><div><dt>当前来源</dt><dd>{{ currentSource?.name ?? '全部来源' }}</dd></div></dl></template></aside></section><section class="evidence-note"><b>文档何时可用于证据问答？</b><span>解析成功并完成当前索引后，文档才能作为本地证据来源。</span></section></template>
<style scoped>
.workspace{display:grid;grid-template-columns:205px minmax(0,1fr) 252px;gap:18px;margin-top:20px}.panel{border:1px solid var(--border-subtle);border-radius:12px;background:#fff;box-shadow:0 1px 2px rgba(16,33,61,.04)}.scope{padding:16px 10px}.scope h2{margin:0;padding:0 7px 11px;font-size:.88rem}.scope button,.scope a{display:flex;width:100%;justify-content:space-between;gap:8px;padding:7px;border:0;border-radius:7px;background:transparent;color:var(--text-muted);font:inherit;font-size:.8rem;text-align:left;text-decoration:none}.scope button.active{background:var(--color-primary-soft);color:var(--color-primary);font-weight:700}.scope b{color:inherit;font-size:.72rem}.list{overflow:hidden}.list-header{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 14px;border-bottom:1px solid var(--border-subtle);color:var(--text-muted);font-size:.78rem}.bulk,.result,.error{margin:0;padding:9px 14px;font-size:.78rem}.bulk{background:#fafcff;color:var(--color-primary)}.bulk button,.pagination button,.error button{margin-left:8px;border:0;background:transparent;color:inherit;font:inherit;font-weight:700}.result{color:var(--text-muted)}.error{color:var(--color-danger);background:var(--color-danger-soft)}.pagination{display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-top:1px solid var(--border-subtle);color:var(--text-muted);font-size:.75rem}.pagination button{margin:0;padding:5px 8px;border:1px solid var(--border-subtle);border-radius:5px;background:#fff;color:var(--color-primary)}.detail{padding:16px}.detail h2{margin:0;font-size:.95rem;overflow-wrap:anywhere}.detail p{color:var(--text-muted);font-size:.76rem}.detail dl{margin:14px 0;border-top:1px solid var(--border-subtle);border-bottom:1px solid var(--border-subtle)}.detail dl div{display:flex;justify-content:space-between;gap:8px;padding:7px 0;font-size:.75rem}.detail dt{color:var(--text-muted)}.detail dd{margin:0;color:var(--ink-900,#10213d);text-align:right}.detail a{color:var(--color-primary);font-size:.78rem;font-weight:700;text-decoration:none}.detail-error{color:var(--color-danger)!important}.evidence-note{display:flex;gap:14px;margin-top:20px;padding:15px 20px;border:1px solid var(--border-subtle);border-radius:12px;background:#fff;font-size:.78rem}.evidence-note span{color:var(--text-muted)}@media(max-width:1100px){.workspace{grid-template-columns:185px minmax(0,1fr)}.detail{display:none}}@media(max-width:700px){.workspace{grid-template-columns:1fr}.scope{display:flex;gap:5px;overflow:auto}.scope h2{display:none}.scope button,.scope a{min-width:max-content}.list-header{align-items:flex-start;flex-direction:column}.evidence-note{flex-direction:column}}
</style>
