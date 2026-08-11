<script setup lang="ts">
import { computed, onMounted, ref, shallowRef, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { researchContextsApi, type ResearchContext } from "../../api/researchContexts";
import {
  writingProjectsApi,
  type ContentSegment,
  type DisclosureDraft,
  type GeneratedContent,
  type WritingEvidenceReference,
  type WritingProject,
  type WritingVersion,
} from "../../api/writingProjects";
import WritingEvidenceDrawer from "../../components/writing/WritingEvidenceDrawer.vue";
import WritingEvidencePanel from "../../components/writing/WritingEvidencePanel.vue";
import { reconcileDraftSegments } from "../../utils/writingSegments";

const route = useRoute();
const router = useRouter();
const project = shallowRef<WritingProject | null>(null);
const draft = shallowRef("");
const draftSegments = shallowRef<ContentSegment[]>([]);
const versions = shallowRef<WritingVersion[]>([]);
const disclosure = shallowRef<DisclosureDraft | null>(null);
const contexts = shallowRef<ResearchContext[]>([]);
const selectedReference = shallowRef<WritingEvidenceReference | null>(null);
const selectedSegmentId = ref("");
const saving = shallowRef(false);
const error = shallowRef("");

const projectId = computed(() => Number(route.params.id));
const activeContext = computed(() =>
  contexts.value.find((context) => context.id === project.value?.research_context_id) ?? null,
);

function contentFromDraft(current: GeneratedContent): GeneratedContent {
  const segments = reconcileDraftSegments(draftSegments.value, draft.value);
  draftSegments.value = segments;
  return {
    ...current,
    sections: [{ id: "draft", title: "草稿", draft: draft.value }],
    segments,
  };
}

function setDraftFromContent(content: GeneratedContent): void {
  draft.value = content.sections.map((section) => section.draft).join("\n\n");
  draftSegments.value = reconcileDraftSegments(content.segments, draft.value);
  selectedSegmentId.value = draftSegments.value[0]?.id ?? "";
}

watch(draft, (nextDraft) => {
  draftSegments.value = reconcileDraftSegments(draftSegments.value, nextDraft);
  if (!draftSegments.value.some((segment) => segment.id === selectedSegmentId.value)) {
    selectedSegmentId.value = draftSegments.value[0]?.id ?? "";
  }
});

async function load(): Promise<void> {
  try {
    const [loadedProject, loadedVersions, loadedDisclosure, loadedContexts] = await Promise.all([
      writingProjectsApi.get(projectId.value),
      writingProjectsApi.listVersions(projectId.value),
      writingProjectsApi.getDisclosure(projectId.value),
      researchContextsApi.list(),
    ]);
    project.value = loadedProject;
    setDraftFromContent(loadedProject.generated_content);
    versions.value = loadedVersions;
    disclosure.value = loadedDisclosure;
    contexts.value = loadedContexts;
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "无法读取写作项目。";
  }
}

async function save(): Promise<boolean> {
  if (!project.value) return false;
  saving.value = true;
  error.value = "";
  try {
    project.value = await writingProjectsApi.updateContent(
      project.value,
      contentFromDraft(project.value.generated_content),
    );
    return true;
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "保存失败；如有版本冲突，请重新打开项目。";
    return false;
  } finally {
    saving.value = false;
  }
}

async function bindDocumentEvidence(documentId: number): Promise<void> {
  if (!project.value || !selectedSegmentId.value) return;
  saving.value = true;
  try {
    // 先保存稳定段落 ID，再创建引用，避免引用指向仅存在于浏览器内的临时段落。
    if (!(await save())) return;
    await writingProjectsApi.addDocumentEvidence(project.value.id, selectedSegmentId.value, documentId);
    project.value = await writingProjectsApi.get(project.value.id);
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "无法绑定所选证据。";
  } finally {
    saving.value = false;
  }
}

async function snapshot(): Promise<void> {
  if (!project.value || !(await save())) return;
  try {
    await writingProjectsApi.saveVersion(project.value);
    versions.value = await writingProjectsApi.listVersions(project.value.id);
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "无法保存版本快照。";
  }
}

async function restore(version: WritingVersion): Promise<void> {
  if (!project.value) return;
  saving.value = true;
  try {
    project.value = await writingProjectsApi.restoreVersion(project.value, version.version);
    setDraftFromContent(project.value.generated_content);
    versions.value = await writingProjectsApi.listVersions(project.value.id);
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "无法恢复该版本。";
  } finally {
    saving.value = false;
  }
}

onMounted(() => void load());
</script>

<template>
  <main class="editor">
    <header class="header">
      <div>
        <p class="eyebrow">WRITING EDITOR · LIVE</p>
        <h1 class="heading">{{ project?.name ?? "写作项目" }}</h1>
        <p class="meta">研究上下文：{{ activeContext?.name ?? "未关联" }} · 版本 {{ project?.version ?? "-" }}</p>
      </div>
      <div class="actions">
        <button :disabled="saving || !project" @click="save">保存草稿</button>
        <button :disabled="saving || !project" @click="snapshot">保存快照</button>
      </div>
    </header>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <div v-if="project" class="workspace">
      <section class="draft-area">
        <label class="segment-label">
          绑定到段落
          <select v-model="selectedSegmentId">
            <option v-for="(segment, index) in draftSegments" :key="segment.id" :value="segment.id">段落 {{ index + 1 }}</option>
            <option v-if="!draftSegments.length" value="">暂无可绑定段落</option>
          </select>
        </label>
        <textarea v-model="draft" aria-label="写作草稿" placeholder="在此撰写或编辑草稿。"></textarea>
        <section class="versions">
          <h2>版本快照</h2>
          <button v-for="version in versions" :key="version.version" :disabled="saving" @click="restore(version)">
            恢复 v{{ version.version }}（{{ version.evidence_references.length }} 条引用）
          </button>
          <p v-if="!versions.length">尚无快照。</p>
        </section>
      </section>
      <WritingEvidencePanel
        :references="project.evidence_references"
        :context-document-ids="activeContext?.document_ids ?? []"
        :selected-segment-id="selectedSegmentId"
        :is-busy="saving || !selectedSegmentId"
        @bind-document="bindDocumentEvidence"
        @open-reference="selectedReference = $event"
      />
    </div>
    <p v-else-if="!error" class="loading">正在读取项目…</p>
  </main>
  <WritingEvidenceDrawer
    :reference="selectedReference"
    @close="selectedReference = null"
    @open-document="router.push(`/documents/${$event}`)"
  />
</template>

<style scoped>
.editor{max-width:1280px;padding:1.5rem;margin:0 auto}.header{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start}.eyebrow{margin:0;color:var(--color-primary);font-size:.72rem;font-weight:900;letter-spacing:.12em}.heading{margin:.25rem 0}.meta,.loading{color:var(--text-muted)}.actions{display:flex;gap:.5rem;flex-wrap:wrap}.actions button,.versions button{border:0;border-radius:7px;padding:.55rem .75rem;background:var(--color-primary);color:#fff;font:inherit;font-weight:700;cursor:pointer}.workspace{display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:1rem;margin-top:1rem}.segment-label{display:grid;gap:.35rem;color:var(--text-muted);font-size:.85rem}.segment-label select{max-width:220px;padding:.45rem;border:1px solid var(--border-subtle);border-radius:7px;background:var(--paper);font:inherit}.draft-area textarea{box-sizing:border-box;width:100%;min-height:440px;margin-top:.65rem;padding:1rem;border:1px solid var(--border-subtle);border-radius:var(--radius-md);font:inherit;line-height:1.65;resize:vertical}.versions{display:flex;gap:.5rem;align-items:center;flex-wrap:wrap;margin-top:.75rem}.versions h2,.versions p{margin:0;font-size:.9rem}.error{padding:.7rem;border-radius:7px;background:var(--color-danger-soft);color:var(--color-danger)}@media(max-width:850px){.header{display:block}.actions{margin-top:.75rem}.workspace{grid-template-columns:1fr}}
</style>
