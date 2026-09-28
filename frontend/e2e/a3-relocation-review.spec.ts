import { test, expect } from "@playwright/test";

test("reviewer compares a relocation and explicitly confirms it", async ({ page }) => {
  const issue = { asset_type: "document_annotation", asset_id: 41, original_anchor_id: 700,
    resolved_anchor_id: null, resolution_status: "relocation_required", resolution_version: 3, candidate_count: 1 };
  const candidate = { id: 900, source_anchor_id: 700, target_anchor_revision_id: 1, candidate_anchor_id: 800,
    method: "quote_exact", algorithm_version: "a3-relocation-1",
    score_breakdown: { quote_exactness: 1, protected_token_match: 1, candidate_uniqueness: 1 },
    protected_token_status: "match", status: "proposed", decision_source: null, created_at: "2026-08-31T00:00:00Z" };
  await page.route("**/api/v1/documents/1/anchor-resolution-issues", route => route.fulfill({ json: [issue] }));
  await page.route("**/api/v1/documents/1/anchor-manifest", route => route.fulfill({ json: {
    revision: { id: 1, file_hash: "a".repeat(64), state: "ready" },
  } }));
  await page.route("**/api/v1/documents/1/segmentation-manifest", route => route.fulfill({ json: {
    segmentation: { id: 2, anchor_revision_id: 1, state: "ready" },
  } }));
  await page.route("**/api/v1/source-anchors/700/relocation-candidates", route => route.fulfill({ json: [candidate] }));
  await page.route(/\/api\/v1\/source-anchors\/700$/, route => route.fulfill({ json: { id: 700, document_id: 1,
    anchor_revision_id: 10, file_hash: "b".repeat(64), extraction_fingerprint: null, quote: "Dose 5 mg",
    quote_hash: "q".repeat(64), resolution_status: "unresolved", quality_status: "eligible", fragments: [], segment_ids: [], created_at: "2026-08-31T00:00:00Z" } }));
  await page.route(/\/api\/v1\/source-anchors\/800$/, route => route.fulfill({ json: { id: 800, document_id: 1,
    anchor_revision_id: 1, file_hash: "a".repeat(64), extraction_fingerprint: null, quote: "Dose 5 mg",
    quote_hash: "q".repeat(64), resolution_status: "exact", quality_status: "eligible", fragments: [], segment_ids: [], created_at: "2026-08-31T00:00:00Z" } }));
  let decisionBody: Record<string, unknown> | null = null;
  await page.route("**/api/v1/source-anchors/700/relocations/900/decisions", async route => {
    decisionBody = route.request().postDataJSON();
    await route.fulfill({ json: { ...issue, original_anchor_id: 700, resolved_anchor_id: 800,
      resolution_status: "relocated_verified", resolution_version: 4 } });
  });

  await page.goto("/documents/1");
  await page.getByRole("tab", { name: "批注", exact: true }).click();
  await expect(page.getByRole("heading", { name: "原文版本待确认" })).toBeVisible();
  await page.getByRole("button", { name: /审核 document_annotation/ }).click();
  await expect(page.getByText("旧版本原文")).toBeVisible();
  await expect(page.getByText("保护表达：一致")).toBeVisible();
  await page.getByRole("button", { name: "确认位置" }).click();
  expect(decisionBody).toMatchObject({ candidate_id: 900, decision: "confirm", expected_resolution_version: 3 });
});
