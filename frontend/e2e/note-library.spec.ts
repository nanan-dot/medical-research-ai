import { expect, test } from "@playwright/test";

const noteFixtures = [
  ["SGLT2 对 CKD 的肾保护作用可能独立于降糖", "整理临床观察与机制解释的关系，进一步探讨哪些观点有直接证据支持。", ["机制", "Discussion"], "DAPA-CKD、EMPA-KIDNEY", "2026-09-01T02:42:00Z"],
  ["DAPA-CKD 与 EMPA-KIDNEY 的人群异质性值得单独讨论", "DAPA-CKD 以 UACR ≥ 200 mg/g 的人群为主，受益主要来自蛋白尿显著改善。", ["人群异质性", "证据对比"], "DAPA-CKD、EMPA-KIDNEY", "2026-08-31T10:15:00Z"],
  ["KDIGO 2023 指南中的推荐强度与 RCT 证据关系", "指南将 SGLT2i 用于 CKD 列为强推荐，主要基于大型 RCT 的一致阳性结果。", ["机制", "指南", "证据等级"], "KDIGO 2023 Clinical Practice Guideline", "2026-08-30T08:05:00Z"],
  ["Discussion 部分可以如何组织机制解释", "建议以血流动力学—肾小管代谢—炎症/纤维化—临床结局的逻辑组织。", ["机制", "Discussion", "写作"], "多篇机制研究综述", "2026-08-29T13:33:00Z"],
  ["亚组分析：eGFR 低于 30 mL/min 人群的潜在获益", "EMPA-KIDNEY 中 eGFR < 30 的患者仍观察到方向一致的肾脏保护效应。", ["亚组分析", "安全性"], "EMPA-KIDNEY", "2026-08-29T01:12:00Z"],
  ["SGLT2i 与 RAASi 联合策略的长期安全性", "关注高钾风险、急性肾损伤与血容量相关不良事件。", ["安全性", "联合治疗"], "多项真实世界研究", "2026-08-28T09:40:00Z"],
  ["蛋白尿下降幅度与肾结局改善的相关性", "整合 DAPA-CKD 与 EMPA-KIDNEY 的数据，探讨蛋白尿下降与肾结局的剂量反应关系。", ["蛋白尿", "结局指标"], "DAPA-CKD、EMPA-KIDNEY", "2026-08-27T06:22:00Z"],
  ["机制综述：SGLT2i 的多靶点效应", "从血流动力学、代谢重编程、炎症抑制、纤维化逆转等维度梳理证据。", ["机制", "综述"], "多篇机制研究综述", "2026-08-26T03:05:00Z"],
] as const;
const fixtureNotes = noteFixtures.map(([title, excerpt, tags, sourceTitle, contentUpdatedAt], index) => ({
  id: index + 1, current_revision: 1, metadata_version: 1, title, excerpt,
  is_favorite: index === 0 || index === 3, is_archived: false, tags: [...tags],
  research_context_ids: [1], source_count: 1,
  source_summaries: [{ source_type: "paper", source_id: index + 10, title: sourceTitle, status: "accessible" }],
  research_context_summaries: [{ id: 1, name: "SGLT2治疗CKD" }], content_updated_at: contentUpdatedAt,
}));

test("AC-NLF-01/02/03/04/07/08/10/11/12/14/15/18/19/20 completes the note workspace flow", async ({ page }) => {
  await page.setViewportSize({ width: 1774, height: 887 });
  const requests: string[] = [];
  let failNextDraftSave = false;
  await page.route("**/api/v1/note-library/**", async (route) => {
    const request = route.request(); const url = request.url(); requests.push(`${request.method()} ${url}`);
    if (url.includes("/facets")) return route.fulfill({ json: { tags: [{ id: "机制", name: "机制", count: 21 }, { id: "Discussion", name: "Discussion", count: 15 }, { id: "研究设计", name: "研究设计", count: 13 }, { id: "统计方法", name: "统计方法", count: 9 }], research_contexts: [{ id: 1, name: "SGLT2治疗CKD", count: 32 }, { id: 2, name: "糖尿病肾病综述", count: 18 }, { id: 3, name: "CKD药物治疗", count: 14 }], quick_counts: { all: 186, recent: 24, favorite: 8, unlinked_research: 17, archived: 0 } } });
    if (url.includes("/notes/1/draft") && request.method() === "GET") return route.fulfill({ json: { note_id: 1, base_revision: 1, draft_version: 1, title: noteFixtures[0][0], body: "阅读 DAPA-CKD 与 EMPA-KIDNEY 时，我想进一步梳理临床结局与机制解释之间的关系。", sources: [], save_state: "saved", updated_at: "2026-09-01T02:42:00Z" } });
    if (url.includes("/notes/1/draft") && request.method() === "PUT") {
      if (failNextDraftSave) return route.fulfill({ status: 500, json: { detail: "草稿保存失败" } });
      return route.fulfill({ json: { note_id: 1, base_revision: 1, draft_version: 2, title: "更新标题", body: "更新正文", sources: [], save_state: "saved", updated_at: "2026-09-01T00:00:00Z" } });
    }
    if (url.includes("/notes/1/revisions/1?") && request.method() === "GET") return route.fulfill({ json: { revision_no: 1, title: "合成 CKD 笔记", body: "版本一正文", origin: "commit", created_at: "2026-09-01T00:00:00Z", sources: [] } });
    if (url.includes("/notes/1/revisions?") && request.method() === "GET") return route.fulfill({ json: { items: [{ revision_no: 1, title: "合成 CKD 笔记", body: "合成正文。", origin: "commit", created_at: "2026-09-01T00:00:00Z", sources: [] }], total: 1, page: 1, page_size: 20 } });
    if (url.endsWith("/notes/1/revisions") && request.method() === "POST") return route.fulfill({ status: 201, json: { revision_no: 2, title: "更新标题", body: "更新正文", origin: "commit", created_at: "2026-09-01T00:00:00Z", sources: [] } });
    if (url.includes("/notes/1/metadata") && request.method() === "PATCH") return route.fulfill({ json: { id: 1 } });
    if (url.includes("/notes/1/archive") && request.method() === "POST") return route.fulfill({ json: { id: 1 } });
    if (url.includes("/notes?")) return route.fulfill({ json: { items: fixtureNotes, total: 21, all_total: 186, page: 1, page_size: 20, query_fingerprint: "fixture", as_of: "2026-09-01T02:42:00Z" } });
    if (url.includes("/notes/1?")) return route.fulfill({ json: { id: 1, current_revision: 1, metadata_version: 1, title: noteFixtures[0][0], body: "阅读 DAPA-CKD 与 EMPA-KIDNEY 时，我想进一步梳理临床结局与机制解释之间的关系。\n\n目前先分别记录试验观察、人群差异和作者讨论的机制假设。机制解释能否支持当前判断，还需要回到原文核对。\n\n下一步：比较两项研究的纳入标准，补充相关机制研究，并标记每条观点对应的原文片段。", is_favorite: true, is_archived: false, tags: ["机制", "Discussion"], research_context_ids: [1], sources: [{ source_type: "document", source_id: 5, document_id: 5, anchor_id: null, granularity: "document", status: "access_revoked", title: "撤销的合成来源", quote: null, url: null, capabilities: [] }], capabilities: ["local_actor_scope_only", "ai_suggestions_unavailable"], content_updated_at: "2026-09-01T02:42:00Z", created_at: "2026-09-01T00:00:00Z" } });
    return route.fulfill({ json: {} });
  });
  await page.goto("/notes");
  await expect(page.getByRole("heading", { name: "笔记库" })).toBeVisible();
  await expect(page.getByTestId("note-workspace")).toBeVisible();
  await page.getByLabel("搜索笔记").fill("CKD");
  await expect.poll(() => requests.some((value) => value.includes("query=CKD"))).toBeTruthy();
  await page.getByRole("button", { name: /SGLT2 对 CKD/ }).click();
  await expect(page.getByTestId("note-preview")).toContainText("DAPA-CKD");
  await expect(page.getByTestId("note-preview")).toContainText("来源已撤销");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog", { name: "编辑笔记" })).toBeVisible();
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "历史版本" }).last().click();
  await expect(page.getByRole("dialog", { name: "历史版本" })).toContainText("版本 1");
  await page.getByRole("button", { name: "查看内容" }).click();
  await expect(page.getByRole("dialog", { name: "历史版本" })).toContainText("版本一正文");
  await page.getByRole("button", { name: "关闭历史版本" }).click();
  await page.getByRole("button", { name: "继续编辑" }).click();
  await page.getByLabel("标题").fill("更新标题");
  await page.getByLabel("正文").fill("更新正文");
  await page.getByRole("button", { name: "正式保存" }).click();
  await expect.poll(() => requests.some((value) => value.startsWith("POST") && value.includes("/revisions"))).toBeTruthy();
  const revisionRequestCount = requests.filter((value) => value.startsWith("POST") && value.includes("/revisions")).length;
  await page.getByRole("button", { name: "继续编辑" }).click();
  failNextDraftSave = true;
  await page.getByLabel("标题").fill("不应提交的标题");
  await page.getByLabel("正文").fill("不应提交的正文");
  await page.getByRole("button", { name: "正式保存" }).click();
  await expect(page.getByText("保存失败，可重试")).toBeVisible();
  expect(requests.filter((value) => value.startsWith("POST") && value.includes("/revisions"))).toHaveLength(revisionRequestCount);
  await page.getByRole("button", { name: "关闭编辑" }).click();
  const requestCountBeforeClear = requests.length;
  await page.getByLabel("搜索笔记").fill("");
  await expect.poll(() => requests.length).toBeGreaterThan(requestCountBeforeClear);
  await expect(page).toHaveScreenshot("note-library-1774x887.png", { animations: "disabled" });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole("button", { name: "返回笔记列表" })).toBeVisible();
  await page.getByRole("button", { name: "返回笔记列表" }).click();
  await expect(page.getByRole("button", { name: /SGLT2 对 CKD/ })).toBeVisible();
});
