import { computed, readonly, ref, shallowRef } from "vue";

import {
  knowledgeSourcesApi,
  type CreateKnowledgeSource,
  type KnowledgeSource,
} from "../api/knowledgeSources";

export function useKnowledgeSources() {
  const sources = ref<KnowledgeSource[]>([]);
  const loading = shallowRef(false);
  const error = shallowRef<string | null>(null);
  const enabledCount = computed(() => sources.value.filter((source) => source.enabled).length);
  const lastSync = shallowRef<string | null>(null);

  async function run(action: () => Promise<void>): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      await action();
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : "知识源操作失败";
    } finally {
      loading.value = false;
    }
  }

  async function load(): Promise<void> {
    await run(async () => {
      sources.value = await knowledgeSourcesApi.list();
    });
  }

  async function create(payload: CreateKnowledgeSource): Promise<void> {
    await run(async () => {
      const created = await knowledgeSourcesApi.create(payload);
      sources.value = [...sources.value, created];
    });
  }

  async function setEnabled(source: KnowledgeSource, enabled: boolean): Promise<void> {
    await run(async () => {
      const updated = await knowledgeSourcesApi.update(source.id, { enabled });
      sources.value = sources.value.map((item) => (item.id === updated.id ? updated : item));
    });
  }

  async function remove(source: KnowledgeSource): Promise<void> {
    await run(async () => {
      await knowledgeSourcesApi.remove(source.id);
      sources.value = sources.value.filter((item) => item.id !== source.id);
    });
  }
  async function sync(source: KnowledgeSource): Promise<void> { await run(async()=>{const result=await knowledgeSourcesApi.sync(source.id);lastSync.value=result.last_sync_time;await load();}); }

  return {
    sources: readonly(sources),
    loading: readonly(loading),
    error: readonly(error),
    enabledCount,
    load,
    create,
    setEnabled,
    remove,
    sync,
    lastSync: readonly(lastSync),
  };
}
