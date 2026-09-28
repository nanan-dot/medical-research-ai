import { mount } from "@vue/test-utils";
import { expect, test } from "vitest";

import ExportMenu from "./ExportMenu.vue";

test("AC-05 and AC-06 describe the real filtered export and expose only CSV RIS BibTeX", async () => {
  const wrapper = mount(ExportMenu, { props: { exporting: false } });

  await wrapper.get("summary").trigger("click");

  expect(wrapper.text()).toContain("导出文献数据，不包含 PDF 全文");
  expect(wrapper.text()).toContain("当前筛选结果");
  expect(wrapper.findAll("button").map((button) => button.text())).toEqual(expect.arrayContaining(["CSV", "RIS", "BibTeX"]));
  expect(wrapper.text()).not.toContain("已勾选");
  expect(wrapper.text()).not.toContain("PubMed 全量");
});

test("AC-05 emits the selected real backend format and disables duplicate submission", async () => {
  const ready = mount(ExportMenu, { props: { exporting: false } });
  await ready.get('[data-format="ris"]').trigger("click");
  expect(ready.emitted("export")?.[0]).toEqual(["ris"]);

  const busy = mount(ExportMenu, { props: { exporting: true } });
  expect(busy.findAll("button").every((button) => button.attributes("disabled") !== undefined)).toBe(true);
});
