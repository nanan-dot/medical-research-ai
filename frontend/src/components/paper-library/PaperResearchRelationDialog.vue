<script setup lang="ts">
import { computed, nextTick, shallowRef, watch } from "vue";

import { ApiError } from "../../api/client";
import { paperLibraryApi, type PaperOverview, type PaperRelation, type ResearchRole } from "../../api/paperLibrary";
import { researchContextsApi, type ResearchContext } from "../../api/researchContexts";
import BaseIcon from "../ui/BaseIcon.vue";
import { roleLabel } from "./paperLibraryFormatters";

const props = defineProps<{ open: boolean; paper: PaperOverview | null }>();
const emit = defineEmits<{ close: []; changed: [] }>();
const contexts = shallowRef<ResearchContext[]>([]);
const selectedContextId = shallowRef<number | null>(null);
const role = shallowRef<ResearchRole | null>("to_evaluate");
const note = shallowRef("");
const loading = shallowRef(false);
const pending = shallowRef(false);
const error = shallowRef<string | null>(null);
const existingRelation = computed<PaperRelation | null>(() => props.paper?.relations.find((item) => item.research_context_id === selectedContextId.value) ?? null);
const selectedContext = computed(() => contexts.value.find((item) => item.id === selectedContextId.value) ?? null);
const availableContexts = computed(() => {
  const known = new Map(contexts.value.map((item) => [item.id, item]));
  props.paper?.relations.forEach((item) => { if (!known.has(item.research_context_id)) known.set(item.research_context_id, { id: item.research_context_id, name: item.research_name, description: "", document_ids: [], conversation_ids: [], evidence_matrix_ids: [], writing_project_ids: [], literature_search_task_ids: [], created_at: "", updated_at: "" }); });
  return [...known.values()];
});

async function loadContexts(): Promise<void> {
  loading.value = true; error.value = null;
  try { contexts.value = await researchContextsApi.list(); selectedContextId.value = props.paper?.relations[0]?.research_context_id ?? contexts.value[0]?.id ?? null; }
  catch (cause) { error.value = cause instanceof Error ? cause.message : "研究列表暂时无法加载"; }
  finally { loading.value = false; }
}

function hydrateRelation(): void { role.value = existingRelation.value?.role ?? "to_evaluate"; note.value = existingRelation.value?.note ?? ""; error.value = null; }

async function save(): Promise<void> {
  if (!props.paper || !selectedContextId.value || pending.value) return;
  pending.value = true; error.value = null;
  try {
    await paperLibraryApi.upsertRelation(props.paper.id, selectedContextId.value, { role: role.value, note: note.value.trim() || null, expected_version: existingRelation.value?.version ?? null });
    emit("changed");
  } catch (cause) {
    error.value = cause instanceof ApiError && cause.status === 409 ? "这项研究关联已在其他位置更新，请刷新概览后重试。" : cause instanceof Error ? cause.message : "研究关联保存失败";
  } finally { pending.value = false; }
}

async function remove(): Promise<void> {
  if (!props.paper || !existingRelation.value || pending.value) return;
  pending.value = true; error.value = null;
  try { await paperLibraryApi.deleteRelation(props.paper.id, existingRelation.value.research_context_id, existingRelation.value.version); emit("changed"); }
  catch (cause) { error.value = cause instanceof ApiError && cause.status === 409 ? "关系版本已变化，请刷新概览后重试。" : cause instanceof Error ? cause.message : "研究关联删除失败"; }
  finally { pending.value = false; }
}

watch(() => props.open, async (open) => { if (open) { await loadContexts(); await nextTick(); } });
watch(selectedContextId, hydrateRelation);
</script>

<template>
  <Teleport to="body"><div v-if="open" class="relation-layer" @click.self="!pending && emit('close')"><section class="relation-dialog" role="dialog" aria-modal="true" aria-labelledby="relation-title" @keydown.esc.prevent="!pending && emit('close')"><header><div><h2 id="relation-title">管理研究关联</h2><p>{{ paper?.title ?? "当前论文" }}</p></div><button type="button" aria-label="关闭研究关联" :disabled="pending" @click="emit('close')"><BaseIcon name="close" /></button></header><div class="relation-form"><p v-if="loading" class="state">正在读取研究项目…</p><template v-else><label for="research-context">关联研究</label><select id="research-context" v-model="selectedContextId"><option v-for="context in availableContexts" :key="context.id" :value="context.id">{{ context.name }}</option></select><p v-if="!availableContexts.length" class="state">还没有可关联的研究项目。请先在“我的研究”中创建研究。</p><label for="research-role">研究角色</label><select id="research-role" v-model="role"><option value="core_evidence">核心证据</option><option value="background_support">背景支持</option><option value="method_reference">方法参考</option><option value="supplementary_reading">补充阅读</option><option value="to_evaluate">待评估</option></select><label for="relation-note">关联说明</label><textarea id="relation-note" v-model="note" rows="4" maxlength="2000" placeholder="说明这篇论文在当前研究中的用途（可选）"></textarea><p v-if="selectedContext" class="relation-summary">将“{{ paper?.title ?? "当前论文" }}”作为“{{ selectedContext.name }}”的{{ roleLabel(role) }}。</p></template><p v-if="error" class="error" role="alert">{{ error }}</p></div><footer><button v-if="existingRelation" class="remove" type="button" :disabled="pending" @click="remove">解除关联</button><span></span><button type="button" :disabled="pending" @click="emit('close')">取消</button><button class="save" type="button" :disabled="pending || !selectedContextId" @click="save">{{ pending ? "正在保存…" : "保存关联" }}</button></footer></section></div></Teleport>
</template>

<style scoped>
.relation-layer{position:fixed;z-index:62;inset:0;display:grid;place-items:center;padding:16px;background:rgb(15 23 42 / 30%)}.relation-dialog{width:min(520px,100%);border:1px solid var(--line);border-radius:8px;background:#fff;box-shadow:0 14px 42px rgb(15 23 42 / 16%)}header{display:flex;justify-content:space-between;gap:15px;padding:19px 20px 14px;border-bottom:1px solid var(--line)}h2{margin:0;font-size:18px}header p{overflow:hidden;max-width:400px;margin:4px 0 0;color:#64748b;font-size:11.5px;text-overflow:ellipsis;white-space:nowrap}header button{display:grid;width:32px;height:32px;place-items:center;border:0;background:transparent;color:#475569}header :deep(.icon){width:18px}.relation-form{display:grid;gap:7px;padding:17px 20px}.relation-form label{margin-top:4px;color:#334155;font-size:12px;font-weight:700}.relation-form select,.relation-form textarea{border:1px solid var(--line);border-radius:5px;padding:0 10px;color:#0f172a;font:inherit;font-size:12.5px}.relation-form select{height:38px;background:#fff}.relation-form textarea{padding-block:8px;resize:vertical}.relation-summary{margin:5px 0 0;padding:9px;border-radius:4px;background:#f3f7ff;color:#475569;font-size:11px;line-height:1.55}.state{color:#64748b;font-size:12px}.error{margin:4px 0 0;color:#c52b2f;font-size:12px}footer{display:grid;grid-template-columns:auto 1fr auto auto;gap:8px;padding:13px 20px 18px;border-top:1px solid var(--line)}footer button{height:36px;border:1px solid var(--line);border-radius:4px;padding:0 13px;background:#fff;color:#334155;font:inherit;font-size:12px;font-weight:700}.save{border-color:#0b5fcc;background:#0b5fcc;color:#fff}.remove{border-color:#fecaca;color:#c52b2f}button:disabled{cursor:not-allowed;opacity:.5}@media(max-width:540px){.relation-layer{align-items:end;padding:0}.relation-dialog{border-radius:10px 10px 0 0}footer{grid-template-columns:1fr 1fr}footer span{display:none}.remove{grid-column:1/-1;order:3}}
</style>
