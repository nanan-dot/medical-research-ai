<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { documentsApi, type DocumentRecord } from "../../api/documents";
import { researchContextsApi, type ResearchContext } from "../../api/researchContexts";
import { writingProjectsApi, type WritingProject, type WritingType } from "../../api/writingProjects";

const router = useRouter();
const projects = ref<WritingProject[]>([]);
const contexts = ref<ResearchContext[]>([]);
const availableDocuments = ref<DocumentRecord[]>([]);
const selectedDocumentIds = ref<number[]>([]);
const name = ref("");
const contextName = ref("");
const selectedContextId = ref<number | null>(null);
const writingType = ref<WritingType>("review");
const error = ref("");
const saving = ref(false);

async function load(): Promise<void> {
  try {
    const [loadedProjects, loadedContexts, documentPage] = await Promise.all([writingProjectsApi.list(), researchContextsApi.list(), documentsApi.list({ parseStatus: "", indexStatus: "" }, 0, 100)]);
    projects.value = loadedProjects;
    contexts.value = loadedContexts;
    availableDocuments.value = documentPage.items;
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "无法读取写作项目。";
  }
}

function toggleDocument(documentId: number, isSelected: boolean): void {
  selectedDocumentIds.value = isSelected ? [...new Set([...selectedDocumentIds.value, documentId])] : selectedDocumentIds.value.filter((id) => id !== documentId);
}

async function linkDocuments(): Promise<void> {
  if (selectedContextId.value === null || !selectedDocumentIds.value.length) return;
  saving.value = true;
  try {
    const updated = await researchContextsApi.addDocuments(selectedContextId.value, selectedDocumentIds.value);
    contexts.value = contexts.value.map((context) => context.id === updated.id ? updated : context);
    selectedDocumentIds.value = [];
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "无法关联所选文档。";
  } finally {
    saving.value = false;
  }
}

async function createContext(): Promise<void> {
  if (!contextName.value.trim()) return;
  saving.value = true;
  try {
    const context = await researchContextsApi.create(contextName.value.trim());
    contexts.value = [context, ...contexts.value];
    selectedContextId.value = context.id;
    contextName.value = "";
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "无法创建研究上下文。";
  } finally {
    saving.value = false;
  }
}

async function create(): Promise<void> {
  if (!name.value.trim()) return;
  saving.value = true;
  error.value = "";
  try {
    const project = await writingProjectsApi.create(name.value.trim(), writingType.value, selectedContextId.value);
    await router.push(`/writing/${project.id}`);
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "无法创建写作项目。";
  } finally {
    saving.value = false;
  }
}

onMounted(() => void load());
</script>

<template>
  <main class="page">
    <header><p class="eyebrow">WRITING PROJECTS · LIVE</p><h1>写作辅助</h1><p>项目、草稿和版本由后端保存；证据只来自已有本地文档、问答或矩阵来源。</p></header>
    <section class="context"><h2>研究上下文</h2><form class="context-create" @submit.prevent="createContext"><input v-model.trim="contextName" maxlength="200" placeholder="新研究上下文名称"><button :disabled="saving || !contextName">创建上下文</button></form><div class="document-link"><p>为已选上下文关联本地文档：</p><label v-for="document in availableDocuments" :key="document.id" class="document-option"><input type="checkbox" :checked="selectedDocumentIds.includes(document.id)" @change="toggleDocument(document.id, ($event.target as HTMLInputElement).checked)"><span>{{ document.original_filename || document.file_path }}</span></label><p v-if="!availableDocuments.length">UNAVAILABLE：文档库没有可关联的本地文档。</p><button :disabled="saving || selectedContextId === null || !selectedDocumentIds.length" @click="linkDocuments">关联所选文档</button></div><p>没有关联文档的上下文会在证据绑定区明确显示 UNAVAILABLE。</p></section>
    <form class="create" @submit.prevent="create"><input v-model.trim="name" maxlength="200" placeholder="项目名称"><select v-model="selectedContextId"><option :value="null">未关联研究上下文</option><option v-for="context in contexts" :key="context.id" :value="context.id">{{ context.name }}（{{ context.document_ids.length }} 篇文档）</option></select><select v-model="writingType"><option value="review">综述</option><option value="proposal">开题</option><option value="reading_note">读书笔记</option><option value="group_meeting">组会</option><option value="introduction">引言</option><option value="discussion">讨论</option><option value="abstract">摘要</option></select><button :disabled="saving || !name">新建项目</button></form>
    <p v-if="error" class="error">{{ error }}</p>
    <section class="grid"><article v-for="project in projects" :key="project.id"><p class="eyebrow">{{ project.writing_type }} · v{{ project.version }}</p><h2>{{ project.name }}</h2><p>研究上下文：{{ project.research_context_id ?? "未关联" }}</p><p>最近更新：{{ new Date(project.updated_at).toLocaleString() }}</p><button @click="router.push(`/writing/${project.id}`)">打开草稿</button></article><p v-if="!projects.length" class="empty">尚无写作项目。</p></section>
  </main>
</template>

<style scoped>
.page{padding:2rem 1.4rem;max-width:1200px}.eyebrow{margin:0;color:var(--color-primary);font-size:.72rem;font-weight:900;letter-spacing:.12em}.page h1{margin:.25rem 0;font-size:2.3rem}.page header>p:last-child,.grid article>p:not(.eyebrow),.context>p{color:var(--text-muted)}.context{margin-top:1rem;padding:1rem;border:1px solid var(--border-subtle);border-radius:var(--radius-md);background:var(--surface-raised)}.context h2{margin:0 0 .5rem;font-size:1.05rem}.context-create,.create{display:flex;gap:.6rem;margin:1.2rem 0}.context-create{margin:.5rem 0}.document-link{display:grid;gap:.4rem;margin:.75rem 0}.document-link p{margin:0}.document-option{display:flex;gap:.5rem;align-items:center;color:var(--text-muted);font-size:.85rem}.document-link button{justify-self:start}.create input,.create select,.context-create input{min-width:0;padding:.6rem;border:1px solid var(--border-subtle);border-radius:7px;background:var(--paper);font:inherit}.create input,.context-create input{flex:1}.create button,.context-create button,.grid article button,.document-link button{border:0;border-radius:7px;padding:.6rem .8rem;background:var(--color-primary);color:#fff;font:inherit;font-weight:750}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.9rem}.grid article,.empty{padding:1rem;border:1px solid var(--border-subtle);border-radius:var(--radius-md);background:var(--paper)}.grid h2{margin:.4rem 0}.error{padding:.7rem;background:var(--color-danger-soft);color:var(--color-danger);border-radius:7px}@media(max-width:720px){.create,.context-create{display:grid}.grid{grid-template-columns:1fr}}
</style>
