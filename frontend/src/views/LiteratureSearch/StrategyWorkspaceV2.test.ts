import { mount } from "@vue/test-utils";
import { expect, test } from "vitest";

import type { SearchStrategyDraft } from "../../types/searchStrategy";
import SearchCenterHeader from "./SearchCenterHeader.vue";
import SearchJourneyProgress from "./SearchJourneyProgress.vue";
import StrategyBasisSection from "./StrategyBasisSection.vue";
import StrategyQuerySection from "./StrategyQuerySection.vue";
import StrategyReadySection from "./StrategyReadySection.vue";
import StrategyStickyBar from "./StrategyStickyBar.vue";
import StrategyTermsMeshSection from "./StrategyTermsMeshSection.vue";
import StrategyLimitsSection from "./StrategyLimitsSection.vue";

const strategy: SearchStrategyDraft = {
  id: 8,
  research_question: "ILD 患者使用尼达尼布的疗效如何？",
  intent_mode: "pico",
  intent: { disease: "间质性肺疾病", intervention: "尼达尼布", comparison: "安慰剂", outcome: "肺功能" },
  limits: {},
  query_text: "ILD[tiab] AND nintedanib[tiab]",
  query_source: "generated",
  fingerprint: "fingerprint",
  revision: 2,
  generation_state: "ready",
  validation_state: "success",
  count_state: "success",
  count: {},
  last_saved_at: "2026-08-23T00:00:00Z",
  terms: [{ id: 3, text: "interstitial lung disease", concept_group: "disease", source: "research_question", field_tag: "tiab", relation_type: "synonym", is_locked: true, warning: null }],
  mesh_terms: [{ id: 4, descriptor: "Lung Diseases, Interstitial", mesh_id: "D017563", concept_group: "disease", source: "nlm_mesh", verification_status: "verified", is_locked: false, verification_checked_at: "2026-08-23T00:00:00Z" }],
};

test("header and journey expose the real state to keyboard and screen readers", async () => {
  const header = mount(SearchCenterHeader, { props: { saveState: "saved", versions: [], canExecute: true } });
  expect(header.text()).toContain("已保存");
  expect(header.text()).toContain("开始检索");
  await header.findAll("button")[0]?.trigger("click");
  expect(header.emitted("createVersion")).toHaveLength(1);
  await header.findAll("button")[1]?.trigger("click");
  expect(header.emitted("execute")).toHaveLength(1);

  const journey = mount(SearchJourneyProgress, { props: { activeStep: 3 } });
  expect(journey.get('[aria-current="step"]').text()).toBe("3");
  expect(journey.text()).toContain("构建检索策略");
});

test("basis renders backend intent, explicitly represents missing fields, and offers the reference edit action", async () => {
  const wrapper = mount(StrategyBasisSection, { props: { strategy } });
  expect(wrapper.text()).toContain("间质性肺疾病");
  expect(wrapper.text()).toContain("尼达尼布");
  expect(wrapper.get("button").text()).toBe("编辑");
  await wrapper.get("button").trigger("click");
  expect(wrapper.emitted("regenerate")).toHaveLength(1);
});

test("terms display persisted MeSH status and expose a real refresh action", async () => {
  const wrapper = mount(StrategyTermsMeshSection, { props: { terms: strategy.terms, meshTerms: strategy.mesh_terms, loading: false } });
  expect(wrapper.text()).toContain("NLM MeSH");
  expect(wrapper.text()).toContain("MeSH 已验证");
  await wrapper.findAll("button").find((item) => item.text() === "重新映射术语")?.trigger("click");
  expect(wrapper.emitted("remap")).toHaveLength(1);
  await wrapper.findAll("button").find((item) => item.text() === "刷新 NLM MeSH")?.trigger("click");
  expect(wrapper.emitted("refreshMesh")).toHaveLength(1);
  await wrapper.get("summary").trigger("click");
  await wrapper.findAll("button").find((item) => item.text() === "解锁首项")?.trigger("click");
  expect(wrapper.emitted("lock")?.[0]).toEqual([3, false]);
  await wrapper.findAll("button").find((item) => item.text() === "添加术语")?.trigger("click");
  await wrapper.get("#strategy-new-term").setValue("fibrosis");
  await wrapper.get("form").trigger("submit");
  expect(wrapper.emitted("add")?.[0]).toEqual([{ text: "fibrosis", conceptGroup: "custom" }]);
  const viewAll = wrapper.findAll("button").find((item) => item.text() === "查看全部");
  await viewAll?.trigger("click");
  expect(wrapper.text()).toContain("收起");
});

test("terms do not claim verification when the persisted MeSH check is unavailable", () => {
  const unavailableStrategy = {
    ...strategy,
    mesh_terms: [{ ...strategy.mesh_terms[0], mesh_id: null, verification_status: "unavailable" as const }],
  };
  const wrapper = mount(StrategyTermsMeshSection, { props: { terms: unavailableStrategy.terms, meshTerms: unavailableStrategy.mesh_terms, loading: false } });
  expect(wrapper.text()).toContain("MeSH 暂不可用");
  expect(wrapper.text()).not.toContain("MeSH 已验证");
});

test("terms retain an unknown backend category instead of rendering a false empty state", () => {
  const wrapper = mount(StrategyTermsMeshSection, {
    props: {
      terms: [{ ...strategy.terms[0], concept_group: "exposure" }],
      meshTerms: [],
      loading: false,
    },
  });
  expect(wrapper.text()).toContain("1 个检索术语");
  expect(wrapper.text()).toContain("其他术语");
  expect(wrapper.text()).toContain("interstitial lung disease");
  expect(wrapper.text()).not.toContain("暂无术语");
  expect(wrapper.text()).toContain("尚未识别标准概念");
  expect(wrapper.text()).not.toContain("当前仅识别到疾病概念");
});

test("coverage notice reflects an empty strategy instead of inventing a disease concept", () => {
  const wrapper = mount(StrategyTermsMeshSection, {
    props: { terms: [], meshTerms: [], loading: false },
  });

  expect(wrapper.text()).toContain("尚未生成检索术语");
  expect(wrapper.text()).not.toContain("当前仅识别到疾病概念");
});

test("non-PICO strategy shows its actual intent instead of empty PICO fields", () => {
  const wrapper = mount(StrategyBasisSection, {
    props: {
      strategy: {
        ...strategy,
        intent_mode: "unstructured",
        research_question: "interstitial lung disease patients",
        intent: {},
      },
    },
  });
  expect(wrapper.text()).toContain("自由关键词检索");
  expect(wrapper.text()).toContain("当前关键词");
  expect(wrapper.text()).not.toContain("人群（Population）");
});

test("query emits edits and validation/count actions without inventing a result", async () => {
  const wrapper = mount(StrategyQuerySection, { props: { strategy, modelValue: strategy.query_text, validation: null, count: null, loading: false } });
  await wrapper.get("textarea").setValue("ILD[tiab]");
  expect(wrapper.emitted("update:modelValue")?.[0]).toEqual(["ILD[tiab]"]);
  await wrapper.get(".heading-actions button:last-child").trigger("click");
  await wrapper.get(".count button").trigger("click");
  expect(wrapper.emitted("validate")).toHaveLength(1);
  expect(wrapper.emitted("refreshCount")).toHaveLength(1);
  expect(wrapper.text()).toContain("当前数值未载入，请刷新");
});

test("ready exposes checks while sticky is the only execution control", async () => {
  const ready = mount(StrategyReadySection, { props: { strategy, validation: null, countAvailable: false, actionError: null } });
  expect(ready.text()).toContain("检索式待验证");
  expect(ready.find("button").exists()).toBe(false);

  const sticky = mount(StrategyStickyBar, { props: { strategy, versions: [], saveState: "saved", executing: false, disabled: true } });
  expect((sticky.get(".execute").element as HTMLButtonElement).disabled).toBe(true);
  expect(sticky.text()).toContain("1 个术语");
  await sticky.get(".version-selector").trigger("click");
  expect(sticky.get(".sticky-version-menu").attributes()).toHaveProperty("open");
});

test("ready state stays honest when unstructured intent and MeSH verification are incomplete", () => {
  const ready = mount(StrategyReadySection, {
    props: {
      strategy: {
        ...strategy,
        intent_mode: "unstructured",
        intent: {},
        validation_state: "pending",
        mesh_terms: [{ ...strategy.mesh_terms[0], verification_status: "not_found", mesh_id: null }],
      },
      validation: null,
      countAvailable: false,
      actionError: null,
    },
  });
  expect(ready.text()).toContain("检索式待验证");
  expect(ready.text()).toContain("研究意图待补充");
  expect(ready.text()).toContain("MeSH 未找到");
  expect(ready.text()).not.toContain("检索策略已准备就绪");
});

test("limits only display backend-provided restrictions", async () => {
  const wrapper = mount(StrategyLimitsSection, { props: { strategy } });
  expect(wrapper.text()).toContain("未设置额外限制");
  await wrapper.get(".limit-action").trigger("click");
  expect(wrapper.emitted("edit")).toHaveLength(1);
});
