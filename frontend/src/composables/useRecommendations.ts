import { computed, onBeforeUnmount, ref, shallowRef, watch, type Ref } from "vue";
import { ApiError } from "../api/client";
import { recommendationApi, type DismissReason, type RecommendationItem, type RecommendationMode, type RecommendationOverlap, type RecommendationPage, type RecommendationSort, type RecommendationStatus } from "../api/recommendations";

const POLL_INTERVAL = 1500;
const PAGE_SIZE = 10;
const INTENT_CONTEXT_MISMATCH = "intent snapshot does not belong to the result research context";
export function useRecommendationsV5(resultId: Ref<number | null>, routeIntentId: Ref<number | null>) {
  const status = shallowRef<RecommendationStatus | null>(null); const page = shallowRef<RecommendationPage | null>(null);
  const loading = ref(false); const syncing = ref(false); const actionPending = ref(false); const error = ref<string | null>(null); const notice = ref<string | null>(null);
  const overlap = ref<RecommendationOverlap>("novel"); const sort = ref<RecommendationSort>("priority");
  const currentPage = shallowRef(1);
  let timer: ReturnType<typeof setTimeout> | null = null; let controller: AbortController | null = null; let listController: AbortController | null = null; let polling = false; let generation = 0;
  const building = computed(() => status.value?.building ?? null); const active = computed(() => status.value?.active ?? null);
  const isBuilding = computed(() => building.value?.status === "queued" || building.value?.status === "running");
  const isNarrating = computed(() => ["pending", "running"].includes(active.value?.narration_status ?? ""));
  const intentSnapshotId = computed(() => active.value?.intent_snapshot_id ?? (isBuilding.value ? building.value?.intent_snapshot_id : null) ?? routeIntentId.value);
  const totalPages = computed(() => Math.max(1, Math.ceil((page.value?.total ?? 0) / PAGE_SIZE)));

  function stop(): void { if (timer) clearTimeout(timer); timer = null; controller?.abort(); listController?.abort(); controller = null; listController = null; polling = false; }
  function message(value: unknown): string { return value instanceof Error ? value.message : "请求失败，请稍后重试"; }
  function isIntentContextMismatch(value: unknown): value is ApiError { return value instanceof ApiError && value.status === 409 && value.message.includes(INTENT_CONTEXT_MISMATCH); }
  async function loadActive(signal?: AbortSignal, expectedGeneration = generation): Promise<void> {
    const requestedResultId = resultId.value; const requestedSort = sort.value; const requestedOverlap = overlap.value; const requestedPage = currentPage.value;
    if (!requestedResultId) return;
    const next = await recommendationApi.getActive(requestedResultId, { page: requestedPage, page_size: PAGE_SIZE, sort: requestedSort, overlap: requestedOverlap }, signal);
    if (expectedGeneration === generation && requestedResultId === resultId.value && requestedSort === sort.value && requestedOverlap === overlap.value && requestedPage === currentPage.value) {
      page.value = next;
      if (requestedOverlap === "novel" && next.novel_count === 0 && next.covered_count > 0) overlap.value = "covered";
    }
  }
  function schedule(currentGeneration: number): void { if ((!isBuilding.value && !isNarrating.value) || currentGeneration !== generation) return; timer = setTimeout(() => void poll(currentGeneration), POLL_INTERVAL); }
  async function poll(currentGeneration = generation): Promise<void> {
    const requestedResultId = resultId.value;
    if (!requestedResultId || polling || currentGeneration !== generation) return;
    polling = true; const local = new AbortController(); controller = local;
    try {
      const previousNarrationStatus = active.value?.narration_status;
      const next = await recommendationApi.getStatus(requestedResultId, local.signal);
      if (local.signal.aborted || currentGeneration !== generation || requestedResultId !== resultId.value) return;
      status.value = next;
      if (next.building?.status === "superseded") notice.value = "该运行已被更新版本取代，已同步最新状态。";
      if (next.active && (!page.value || page.value.run_id !== next.active.run_id || previousNarrationStatus !== next.active.narration_status)) await loadActive(local.signal, currentGeneration);
      const terminal = next.building && ["failed", "cancelled"].includes(next.building.status);
      if (terminal) notice.value = next.building?.status === "failed" ? `新版本生成失败：${next.building.last_error?.message ?? "请重试"}` : "推荐生成已取消。";
    } catch (value) { if (!local.signal.aborted && currentGeneration === generation) error.value = message(value); }
    finally { polling = false; if (controller === local) controller = null; schedule(currentGeneration); }
  }
  async function initialize(): Promise<void> {
    stop(); generation += 1; error.value = null; notice.value = null; const requestedResultId = resultId.value;
    if (!requestedResultId) return;
    loading.value = true; const localGeneration = generation; const local = new AbortController(); controller = local;
    try {
      const next = await recommendationApi.getStatus(requestedResultId, local.signal);
      if (local.signal.aborted || localGeneration !== generation || requestedResultId !== resultId.value) return;
      status.value = next; if (next.active) await loadActive(local.signal, localGeneration); schedule(localGeneration);
    } catch (value) { if (!local.signal.aborted && localGeneration === generation) error.value = message(value); }
    finally { if (localGeneration === generation) loading.value = false; if (controller === local) controller = null; }
  }
  async function createRun(mode: RecommendationMode, candidateCount: number, explorationQuery?: string | null): Promise<void> {
    if (!resultId.value || actionPending.value || isBuilding.value) return;
    actionPending.value = true; error.value = null; notice.value = null;
    const request = { intent_snapshot_id: intentSnapshotId.value, exploration_query: intentSnapshotId.value === null ? explorationQuery?.trim() || null : null, mode, candidate_count: candidateCount, retry_failed: status.value?.can_retry ?? false, force_refresh: active.value !== null };
    try { await recommendationApi.createRun(resultId.value, request); await poll(); }
    catch (value) {
      if (request.intent_snapshot_id !== null && isIntentContextMismatch(value)) {
        routeIntentId.value = null;
        notice.value = "检测到旧链接中的研究意图不属于当前结果，已改为基于当前检索快照生成探索推荐。";
        try { await recommendationApi.createRun(resultId.value, { ...request, intent_snapshot_id: null, retry_failed: false, force_refresh: false }); await poll(); }
        catch (retryValue) { error.value = message(retryValue); await poll(); }
      } else { error.value = message(value); await poll(); }
    } finally { actionPending.value = false; }
  }
  async function cancel(): Promise<void> { if (!resultId.value || actionPending.value) return; actionPending.value = true; try { await recommendationApi.cancel(resultId.value); await poll(); } catch (value) { error.value = message(value); } finally { actionPending.value = false; } }
  async function refreshList(): Promise<void> {
    if (!resultId.value || !active.value) return;
    listController?.abort(); const local = new AbortController(); listController = local; syncing.value = true; error.value = null;
    try { await loadActive(local.signal); } catch (value) { if (!local.signal.aborted) error.value = message(value); }
    finally { if (listController === local) { listController = null; syncing.value = false; } }
  }
  async function goToPage(nextPage: number): Promise<void> {
    const pageNumber = Math.max(1, Math.min(nextPage, totalPages.value));
    if (pageNumber === currentPage.value) return;
    currentPage.value = pageNumber;
    await refreshList();
  }
  async function decide(item: RecommendationItem, decision: "accepted" | "dismissed", reason?: DismissReason): Promise<void> {
    if (!resultId.value || !page.value) return;
    const requestedResultId = resultId.value; const runId = page.value.run_id; const previous = item.decision; const optimistic = { ...item, decision: { decision, dismiss_reason: reason ?? null } };
    const update = (transform: (entry: RecommendationItem) => RecommendationItem | null) => { if (page.value?.run_id === runId) page.value = { ...page.value, items: page.value.items.flatMap(entry => { const next = entry.pmid === item.pmid ? transform(entry) : entry; return next ? [next] : []; }) }; };
    update(() => optimistic);
    try { const saved = decision === "accepted" ? await recommendationApi.accept(requestedResultId, runId, item.pmid) : await recommendationApi.dismiss(requestedResultId, runId, item.pmid, reason!); update(entry => decision === "dismissed" && overlap.value === "novel" ? null : { ...entry, decision: saved }); }
    catch (value) { update(entry => ({ ...entry, decision: previous })); throw value; }
  }
  watch(resultId, (next, previous) => { if (next !== previous) { page.value = null; status.value = null; currentPage.value = 1; } void initialize(); }, { immediate: true });
  watch([overlap, sort], () => { currentPage.value = 1; void refreshList(); }); onBeforeUnmount(stop);
  return { status, page, loading, syncing, actionPending, error, notice, overlap, sort, currentPage, totalPages, active, building, isBuilding, isNarrating, intentSnapshotId, initialize, createRun, cancel, refreshList, goToPage, decide };
}
