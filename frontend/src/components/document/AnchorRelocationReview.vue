<script setup lang="ts">
import { shallowRef, watch } from "vue";

import { sourceAnchorsApi } from "../../api/sourceAnchors";
import { sourceRelocationsApi } from "../../api/sourceRelocations";
import type { SourceAnchor } from "../../types/sourceAnchors";
import type { RelocationCandidate, ResolutionIssue } from "../../types/sourceRelocations";

const props = defineProps<{ documentId: number; fileHash: string }>();
const issues = shallowRef<ResolutionIssue[]>([]);
const activeIssue = shallowRef<ResolutionIssue | null>(null);
const candidates = shallowRef<RelocationCandidate[]>([]);
const oldAnchor = shallowRef<SourceAnchor | null>(null);
const candidateAnchors = shallowRef<Record<number, SourceAnchor>>({});
const loading = shallowRef(false);
const error = shallowRef("");
let generation = 0;

function difference(candidateId: number): { prefix: string; oldChanged: string; newChanged: string; suffix: string } {
  const oldText = oldAnchor.value?.quote ?? ""; const newText = candidateAnchors.value[candidateId]?.quote ?? "";
  let start = 0; while (start < oldText.length && start < newText.length && oldText[start] === newText[start]) start++;
  let oldEnd = oldText.length; let newEnd = newText.length;
  while (oldEnd > start && newEnd > start && oldText[oldEnd - 1] === newText[newEnd - 1]) { oldEnd--; newEnd--; }
  return { prefix: oldText.slice(0, start), oldChanged: oldText.slice(start, oldEnd),
    newChanged: newText.slice(start, newEnd), suffix: oldText.slice(oldEnd) };
}

watch(() => [props.documentId, props.fileHash], loadIssues, { immediate: true });

async function loadIssues(): Promise<void> {
  const current = ++generation; activeIssue.value = null; candidates.value = []; error.value = "";
  try { const rows = await sourceRelocationsApi.issues(props.documentId); if (current === generation) issues.value = Array.isArray(rows) ? rows : []; }
  catch (cause) { if (current === generation) error.value = cause instanceof Error ? cause.message : "重定位列表加载失败"; }
}

async function review(issue: ResolutionIssue): Promise<void> {
  const current = ++generation; activeIssue.value = issue; loading.value = true; error.value = "";
  try {
    const [source, existingCandidates] = await Promise.all([
      sourceAnchorsApi.get(issue.original_anchor_id),
      sourceRelocationsApi.candidates(issue.original_anchor_id),
    ]);
    // 已持久化候选可在旧文件不可用时继续供人工审核；只有新生成时才依赖当前 A0/A1 版本。
    const rows = existingCandidates.length
      ? existingCandidates
      : await sourceRelocationsApi.generate(
        issue.original_anchor_id,
        (await sourceAnchorsApi.version(props.documentId, props.fileHash)).expected_anchor_revision_id,
      );
    const anchors = await Promise.all(rows.filter(row => row.candidate_anchor_id).map(async row => [row.id, await sourceAnchorsApi.get(row.candidate_anchor_id!)] as const));
    if (current === generation) { oldAnchor.value = source; candidates.value = rows; candidateAnchors.value = Object.fromEntries(anchors); }
  } catch (cause) { if (current === generation) error.value = cause instanceof Error ? cause.message : "候选生成失败"; }
  finally { if (current === generation) loading.value = false; }
}

async function decide(candidate: RelocationCandidate, decision: "confirm" | "reject"): Promise<void> {
  if (!activeIssue.value || loading.value) return;
  loading.value = true;
  try { await sourceRelocationsApi.decide(activeIssue.value.original_anchor_id, activeIssue.value, candidate.id, decision); await loadIssues(); }
  catch (cause) { error.value = cause instanceof Error ? cause.message : "决策保存失败"; }
  finally { loading.value = false; }
}
</script>

<template>
  <section v-if="issues.length || activeIssue" class="relocation-review" aria-label="原文重定位审核">
    <h3>原文版本待确认</h3>
    <p>候选位置不会自动成为已核验原文，请逐项比较后确认。</p>
    <button v-for="issue in issues" :key="`${issue.asset_type}-${issue.asset_id}`" :disabled="loading" @click="review(issue)">审核 {{ issue.asset_type }} #{{ issue.asset_id }}（{{ issue.candidate_count }} 个候选）</button>
    <p v-if="loading" role="status">正在准备版本对比…</p><p v-if="error" role="alert">{{ error }}</p>
    <article v-if="activeIssue && oldAnchor" class="comparison">
      <h4>旧版本原文</h4><blockquote>{{ oldAnchor.quote }}</blockquote>
      <section v-for="candidate in candidates" :key="candidate.id" class="candidate">
        <h4>新版本候选</h4><blockquote>{{ candidateAnchors[candidate.id]?.quote }}</blockquote>
        <p class="character-diff" aria-label="字符级差异"><span>{{ difference(candidate.id).prefix }}</span><del>{{ difference(candidate.id).oldChanged }}</del><ins>{{ difference(candidate.id).newChanged }}</ins><span>{{ difference(candidate.id).suffix }}</span></p>
        <p>方法：{{ candidate.method }} · 保护表达：{{ candidate.protected_token_status === 'match' ? '一致' : '不一致，禁止确认' }}</p>
        <dl><template v-for="(score, name) in candidate.score_breakdown" :key="name"><dt>{{ name }}</dt><dd>{{ score.toFixed(3) }}</dd></template></dl>
        <button :disabled="loading || candidate.protected_token_status !== 'match'" @click="decide(candidate, 'confirm')">确认位置</button>
        <button :disabled="loading" @click="decide(candidate, 'reject')">不是此处</button>
      </section>
    </article>
  </section>
</template>

<style scoped>
.relocation-review { display: grid; gap: .6rem; border-top: 1px solid var(--border-subtle); padding-top: 1rem; } h3, h4, p { margin: 0; } h3 { font-size: 1rem; } p, blockquote, dl { font-size: .78rem; } button { justify-self: start; border: 1px solid var(--border-strong); border-radius: 6px; padding: .4rem .55rem; background: var(--paper); color: var(--text-primary); } .comparison, .candidate { display: grid; gap: .45rem; } .candidate { border: 1px solid var(--border-subtle); border-radius: 8px; padding: .65rem; } blockquote { margin: 0; padding-left: .55rem; border-left: 2px solid var(--color-primary); } .character-diff { font-family: ui-monospace, monospace; } del { background: #fee2e2; } ins { background: #dcfce7; text-decoration: none; } dl { display: grid; grid-template-columns: 1fr auto; margin: 0; } dt, dd { margin: 0; }
</style>
