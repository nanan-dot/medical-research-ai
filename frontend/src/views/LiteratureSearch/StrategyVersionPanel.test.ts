import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import StrategyVersionPanel from "./StrategyVersionPanel.vue";

describe("StrategyVersionPanel", () => {
  it("labels strategy snapshots separately from results and compares the latest pair", async () => {
    const wrapper = mount(StrategyVersionPanel, {
      props: {
        versions: [
          { id: 2, strategy_id: 1, version: 2, fingerprint: "next", note: null, created_at: "2026-08-23T00:00:00Z" },
          { id: 1, strategy_id: 1, version: 1, fingerprint: "first", note: null, created_at: "2026-08-22T00:00:00Z" },
        ],
        comparison: null,
        loading: false,
        error: null,
      },
    });

    expect(wrapper.text()).toContain("不会替代检索结果版本");
    await wrapper.get(".compare-button").trigger("click");
    expect(wrapper.emitted("compare")).toEqual([[1, 2]]);
  });
});
