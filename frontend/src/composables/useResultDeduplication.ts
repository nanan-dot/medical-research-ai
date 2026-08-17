import { computed, shallowRef } from "vue";

import {
  literatureSearchApi,
  type DeduplicationSummary,
  type DuplicateGroup,
  type ResultDuplicateResolutionRequest,
} from "../api/literatureSearch";

const GROUP_PAGE_SIZE = 10;
type DuplicateGroupStatus = "pending_resolution" | "all";

/** 管理结果快照的真实去重状态；所有扫描和决策都由服务端返回值驱动。 */
export function useResultDeduplication(resultId: number, onChanged: () => void) {
  const summary = shallowRef<DeduplicationSummary | null>(null);
  const groups = shallowRef<DuplicateGroup[]>([]);
  const status = shallowRef<DuplicateGroupStatus>("pending_resolution");
  const offset = shallowRef(0);
  const total = shallowRef(0);
  const loading = shallowRef(false);
  const error = shallowRef("");
  const page = computed(() => Math.floor(offset.value / GROUP_PAGE_SIZE) + 1);
  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / GROUP_PAGE_SIZE)));

  async function loadSummary(): Promise<void> {
    try {
      summary.value = await literatureSearchApi.getDeduplicationSummary(resultId);
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : "无法读取重复论文摘要";
    }
  }

  async function loadGroups(nextStatus = status.value, nextOffset = offset.value): Promise<void> {
    loading.value = true;
    error.value = "";
    try {
      const groupPage = await literatureSearchApi.listResultDuplicateGroups(resultId, nextStatus, nextOffset, GROUP_PAGE_SIZE);
      status.value = nextStatus;
      offset.value = groupPage.offset;
      total.value = groupPage.total;
      groups.value = groupPage.items;
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : "无法读取重复论文分组";
    } finally {
      loading.value = false;
    }
  }

  async function scan(): Promise<void> {
    loading.value = true;
    error.value = "";
    try {
      summary.value = await literatureSearchApi.runResultDeduplication(resultId);
      await loadGroups("pending_resolution", 0);
      onChanged();
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : "重复论文检查失败";
    } finally {
      loading.value = false;
    }
  }

  async function resolve(groupId: number, request: ResultDuplicateResolutionRequest): Promise<void> {
    loading.value = true;
    error.value = "";
    try {
      const response = await literatureSearchApi.resolveResultDuplicateGroup(resultId, groupId, request);
      summary.value = response.summary;
      await loadGroups(status.value, offset.value);
      onChanged();
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : "重复论文判断保存失败";
    } finally {
      loading.value = false;
    }
  }

  return { summary, groups, status, loading, error, page, totalPages, loadSummary, loadGroups, scan, resolve };
}
