import { shallowRef } from "vue";
import { knowledgeSourcesApi, type KnowledgeSource } from "../api/knowledgeSources";

export function useKnowledgeSourceActions(replaceItem: (source: KnowledgeSource) => void) {
  const pendingAction = shallowRef<string | null>(null);
  const actionError = shallowRef<string | null>(null);

  async function updateOptimistically(source: KnowledgeSource, patch: Partial<KnowledgeSource>, actionKey: string): Promise<void> {
    const optimistic = { ...source, ...patch };
    replaceItem(optimistic);
    pendingAction.value = actionKey;
    actionError.value = null;
    try { replaceItem(await knowledgeSourcesApi.update(source.id, patch)); }
    catch (caught) { replaceItem(source); actionError.value = caught instanceof Error ? caught.message : "保存失败，已恢复原状态"; }
    finally { pendingAction.value = null; }
  }

  function togglePinned(source: KnowledgeSource): Promise<void> { return updateOptimistically(source, { is_pinned: !source.is_pinned }, `pin-${source.id}`); }
  function toggleAutoSync(source: KnowledgeSource, autoSync: boolean): Promise<void> { return updateOptimistically(source, { auto_sync: autoSync }, `auto-${source.id}`); }
  async function sync(source: KnowledgeSource): Promise<void> {
    const actionKey = `sync-${source.id}`;
    if (pendingAction.value === actionKey) return;
    pendingAction.value = actionKey; actionError.value = null;
    try { await knowledgeSourcesApi.sync(source.id); }
    catch (caught) { actionError.value = caught instanceof Error ? caught.message : "同步任务提交失败"; }
    finally { pendingAction.value = null; }
  }
  async function remove(source: KnowledgeSource): Promise<boolean> {
    const actionKey = `remove-${source.id}`;
    if (pendingAction.value === actionKey) return false;
    pendingAction.value = actionKey; actionError.value = null;
    try { await knowledgeSourcesApi.remove(source.id); return true; }
    catch (caught) { actionError.value = caught instanceof Error ? caught.message : "移除失败"; return false; }
    finally { pendingAction.value = null; }
  }
  return { pendingAction, actionError, togglePinned, toggleAutoSync, sync, remove };
}
