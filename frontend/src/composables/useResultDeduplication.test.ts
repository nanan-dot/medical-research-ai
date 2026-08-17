import { afterEach, describe, expect, test, vi } from "vitest";

import { useResultDeduplication } from "./useResultDeduplication";

// 只 mock 本 composable 实际使用的方法，其余 API 不参与本测试。
vi.mock("../api/literatureSearch", () => ({
  literatureSearchApi: {
    getDeduplicationSummary: vi.fn(),
    runResultDeduplication: vi.fn(),
    listResultDuplicateGroups: vi.fn(),
    resolveResultDuplicateGroup: vi.fn(),
  },
}));

import {
  literatureSearchApi,
  type DeduplicationSummary,
  type DuplicateGroup,
} from "../api/literatureSearch";

const api = vi.mocked(literatureSearchApi);

function makeSummary(overrides: Partial<DeduplicationSummary> = {}): DeduplicationSummary {
  return {
    result_id: 11,
    scanned_count: 500,
    source_visible_count: 500,
    consolidated_visible_count: 485,
    hidden_record_count: 15,
    clear_group_count: 12,
    pending_group_count: 3,
    resolved_merge_group_count: 0,
    resolved_keep_all_group_count: 0,
    has_scan: true,
    generated_at: "2026-08-16T00:00:00Z",
    ...overrides,
  };
}

function makeGroup(overrides: Partial<DuplicateGroup> = {}): DuplicateGroup {
  return {
    id: 1,
    trigger_task_id: 7,
    result_id: 11,
    match_method: "title_normalized",
    confidence: "fuzzy",
    status: "pending_resolution",
    created_at: "2026-08-16T00:00:00Z",
    match_explanation: "题名标准化后相同",
    canonical_record_key: null,
    members: [],
    resolution: null,
    ...overrides,
  };
}

afterEach(() => vi.clearAllMocks());

describe("useResultDeduplication", () => {
  test("scan 触发检查、加载待确认组并回调一次刷新", async () => {
    const onChanged = vi.fn();
    api.runResultDeduplication.mockResolvedValue(makeSummary());
    api.listResultDuplicateGroups.mockResolvedValue({ total: 1, offset: 0, limit: 20, items: [makeGroup()] });

    const { scan } = useResultDeduplication(11, onChanged);
    await scan();

    expect(api.runResultDeduplication).toHaveBeenCalledWith(11);
    expect(api.listResultDuplicateGroups).toHaveBeenCalledWith(11, "pending_resolution", 0, 10);
    expect(onChanged).toHaveBeenCalledTimes(1);
  });

  test("resolve merge 成功后更新 summary、刷新当前待确认页并回调刷新", async () => {
    const onChanged = vi.fn();
    api.listResultDuplicateGroups.mockResolvedValue({ total: 1, offset: 0, limit: 20, items: [makeGroup()] });
    const updatedGroup = makeGroup({ status: "resolved_merged" });
    const updatedSummary = makeSummary({ pending_group_count: 2, resolved_merge_group_count: 1 });
    api.resolveResultDuplicateGroup.mockResolvedValue({ group: updatedGroup, summary: updatedSummary });

    const { groups, summary, loadGroups, resolve } = useResultDeduplication(11, onChanged);
    await loadGroups();
    await resolve(1, { action: "merge", canonical_record_key: "11:0:pmid1" });

    expect(api.resolveResultDuplicateGroup).toHaveBeenCalledWith(11, 1, { action: "merge", canonical_record_key: "11:0:pmid1" });
    expect(summary.value?.pending_group_count).toBe(2);
    expect(api.listResultDuplicateGroups).toHaveBeenLastCalledWith(11, "pending_resolution", 0, 10);
    expect(groups.value[0].status).toBe("pending_resolution");
    expect(onChanged).toHaveBeenCalledTimes(1);
  });

  test("resolve keep_all 成功后回调刷新并重新读取当前分组", async () => {
    const onChanged = vi.fn();
    api.listResultDuplicateGroups.mockResolvedValue({ total: 1, offset: 0, limit: 20, items: [makeGroup()] });
    api.resolveResultDuplicateGroup.mockResolvedValue({
      group: makeGroup({ status: "resolved_keep_all" }),
      summary: makeSummary({ resolved_keep_all_group_count: 1 }),
    });

    const { groups, loadGroups, resolve } = useResultDeduplication(11, onChanged);
    await loadGroups();
    await resolve(1, { action: "keep_all" });

    expect(api.listResultDuplicateGroups).toHaveBeenLastCalledWith(11, "pending_resolution", 0, 10);
    expect(onChanged).toHaveBeenCalledTimes(1);
  });

  test("resolve undo 成功后回调刷新并恢复待确认分组", async () => {
    const onChanged = vi.fn();
    api.listResultDuplicateGroups.mockResolvedValue({ total: 1, offset: 0, limit: 20, items: [makeGroup({ status: "resolved_merged" })] });
    api.resolveResultDuplicateGroup.mockResolvedValue({
      group: makeGroup({ status: "pending_resolution" }),
      summary: makeSummary({ pending_group_count: 3 }),
    });

    const { groups, loadGroups, resolve } = useResultDeduplication(11, onChanged);
    await loadGroups();
    await resolve(1, { action: "undo" });

    expect(api.listResultDuplicateGroups).toHaveBeenLastCalledWith(11, "pending_resolution", 0, 10);
    expect(onChanged).toHaveBeenCalledTimes(1);
  });

  test("决策失败时不回调刷新、保留错误信息", async () => {
    const onChanged = vi.fn();
    api.resolveResultDuplicateGroup.mockRejectedValue(new Error("网络失败"));

    const { error, resolve } = useResultDeduplication(11, onChanged);
    await resolve(1, { action: "undo" });

    expect(onChanged).not.toHaveBeenCalled();
    expect(error.value).toBe("网络失败");
  });
});
