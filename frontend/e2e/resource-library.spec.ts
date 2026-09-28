import { expect, test, type Page, type Route } from "@playwright/test";

const resourceItems = [
  {
    id: 7, knowledge_source_id: 1, file_path: "ild/ild-treatment-review.pdf", original_filename: "ILD-treatment-review.pdf", file_type: "pdf", media_type: "application/pdf", file_hash: "fixture-7", file_size: 5_872_640, modified_time: "2026-08-20T14:35:00Z", scan_state: "pending", parse_status: "succeeded", index_status: "succeeded", error_code: null, error_message: null, retry_count: 0, started_at: null, finished_at: null, parsed_is_scanned: false, source_name: "ILD 核心文献", source_type: "local_folder", relative_path: "ILD 核心文献 / ILD-treatment-review.pdf", display_name: "ILD-treatment-review.pdf", task_status: null, phase: null, current_item: null, last_opened_at: null, open_count: 0, status: "ai_available", match_fields: [], snippet: null, locator: null,
  },
  {
    id: 8, knowledge_source_id: 1, file_path: "ild/protocol.docx", original_filename: "文献名称汇总.docx", file_type: "docx", media_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document", file_hash: "fixture-8", file_size: 3_200_000, modified_time: "2026-08-19T16:45:00Z", scan_state: "pending", parse_status: "succeeded", index_status: "pending", error_code: null, error_message: null, retry_count: 0, started_at: null, finished_at: null, parsed_is_scanned: false, source_name: "ILD 核心文献", source_type: "local_folder", relative_path: "ILD 核心文献 / 文献名称汇总.docx", display_name: "文献名称汇总.docx", task_status: "running", phase: "建立索引", current_item: "文献名称汇总.docx", last_opened_at: null, open_count: 0, status: "processing", match_fields: [], snippet: null, locator: null,
  },
  {
    id: 9, knowledge_source_id: 2, file_path: "vault/notes.md", original_filename: "SGLT2 机制研究笔记.md", file_type: "markdown", media_type: "text/markdown", file_hash: "fixture-9", file_size: 18_000, modified_time: "2026-08-18T20:33:00Z", scan_state: "pending", parse_status: "failed", index_status: "pending", error_code: "parse_failed", error_message: "fixture error", retry_count: 0, started_at: null, finished_at: null, parsed_is_scanned: false, source_name: "IPF Notes Vault", source_type: "obsidian_vault", relative_path: "IPF Notes Vault / notes.md", display_name: "SGLT2 机制研究笔记.md", task_status: null, phase: null, current_item: null, last_opened_at: null, open_count: 0, status: "needs_attention", match_fields: [], snippet: null, locator: null,
  },
];

async function json(route: Route, payload: unknown, status = 200): Promise<void> {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(payload) });
}

async function installLibraryFixture(page: Page, fixtureItems = resourceItems, fixtureTotal = 43): Promise<void> {
  // The app shell preloads the literature-search command palette. Keep that
  // unrelated request inside the fixture so its unavailable backend cannot
  // make this resource-library acceptance test noisy.
  await page.route("**/api/v1/literature-search**", async (route) =>
    json(route, { items: [], total: 0, offset: 0, limit: 50 }),
  );
  await page.route("**/api/v1/documents/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/preview")) {
      return json(route, { document_id: 7, kind: "unavailable", content_url: null, blocks: [], tables: [], message: "该文件暂不支持在线预览。" });
    }
    return json(route, { detail: "fixture route unavailable" }, 404);
  });
  await page.route("**/api/v1/library/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path.endsWith("/summary")) return json(route, { total: 43, processed: 38, ai_available: 31, processing: 4, needs_attention: 3, issue_breakdown: { parse_failed: 2, unsupported_format: 0, unavailable_file: 0, index_failed: 1, other: 0 }, source_types: [], snapshot_at: "2026-08-30T00:00:00Z" });
    if (path.endsWith("/source-tree")) return json(route, { groups: [
      { source_type: "local", node_id: "group:local", descendant_count: 32, health: "ready", children: [{ node_id: "source:1", parent_id: "group:local", name: "ILD 核心文献", relative_path: "", source_id: 1, direct_count: 0, descendant_count: 32, health: "ready", children: [{ node_id: "tree:1:trials", parent_id: "source:1", name: "临床试验", relative_path: "trials", source_id: 1, direct_count: 8, descendant_count: 8, health: "ready", children: [] }] }] },
      { source_type: "obsidian", node_id: "group:obsidian", descendant_count: 11, health: "ready", children: [{ node_id: "source:2", parent_id: "group:obsidian", name: "IPF Notes Vault", relative_path: "", source_id: 2, direct_count: 11, descendant_count: 11, health: "ready", children: [] }] },
      { source_type: "zotero", node_id: "group:zotero", descendant_count: 0, health: "unavailable", children: [] },
    ] });
    if (path.endsWith("/recent")) return json(route, { items: [resourceItems[0]], total: 1, offset: 0, limit: 5 });
    if (path.endsWith("/storage")) return json(route, { managed_bytes: 134_217_728, external_source_bytes: 0, total_known_bytes: 134_217_728, quota_bytes: null, usage_percent: null, status: "not_configured", measured_at: "2026-08-30T00:00:00Z" });
    if (path.endsWith("/facets")) return json(route, { sources: [{ value: "1", count: 32 }, { value: "2", count: 11 }], source_types: [], file_types: [{ value: "pdf", count: 1 }, { value: "docx", count: 1 }, { value: "markdown", count: 1 }], statuses: [{ value: "ai_available", count: 1 }, { value: "processing", count: 1 }, { value: "needs_attention", count: 1 }] });
    if (path.endsWith("/items/7/opened")) return json(route, { document_id: 7, last_opened_at: "2026-08-30T00:00:00Z", last_opened_by: null, open_count: 1 });
    if (path.endsWith("/items/9/repair")) return json(route, { task_id: 99 }, 202);
    if (path.endsWith("/items")) {
      const query = url.searchParams.get("q");
      const sourceId = url.searchParams.get("source_id");
      const items = query === "noresult" ? [] : sourceId === "2" ? [resourceItems[2]] : fixtureItems;
      return json(route, { items, total: query === "noresult" ? 0 : sourceId === "2" ? 11 : fixtureTotal, offset: Number(url.searchParams.get("offset") ?? 0), limit: Number(url.searchParams.get("limit") ?? 25) });
    }
    return json(route, { detail: "fixture route unavailable" }, 404);
  });
}

async function screenshotRegions(page: Page, suffix: string): Promise<void> {
  const root = "../docs/frontend-rebuild/screenshots/resource-library";
  await page.screenshot({ path: `${root}/resource-library-${suffix}.png`, fullPage: true });
  for (const [name, selector] of Object.entries({ title: ".documents-heading", summary: ".summary", rail: ".source-nav", toolbar: ".document-filters", task: ".task-banner", table: ".document-list", pagination: ".pagination" })) {
    const region = page.locator(selector);
    if (await region.isVisible()) await region.screenshot({ path: `${root}/resource-library-${suffix}-${name}.png` });
  }
}

test("资料库真实路由、键盘交互和可恢复 URL", async ({ page }) => {
  await installLibraryFixture(page);
  await page.setViewportSize({ width: 1536, height: 960 });
  await page.goto("/documents?page=1&pageSize=25&sort=updated_at&order=desc");

  await expect(page.getByRole("heading", { name: "资料库" })).toBeVisible();
  await expect(page.getByText("当前视图：全部资料")).toBeVisible();
  await expect(page.getByRole("tree", { name: "资料来源树" })).toBeVisible();
  await expect(page.getByText("正在处理 文献名称汇总.docx")).toBeVisible();
  await page.locator('[data-node-id="source:1"]').focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByText("临床试验", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "查看 ILD-treatment-review.pdf" }).click();
  await expect(page.getByRole("dialog", { name: "资料详情" })).toBeVisible();
  await page.getByRole("dialog", { name: "资料详情" }).screenshot({ path: "../docs/frontend-rebuild/screenshots/resource-library/resource-library-1536x960-drawer.png" });
  await expect(page).toHaveURL(/documentId=7/);
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "资料详情" })).toBeHidden();
  await expect(page).not.toHaveURL(/documentId=7/);
  await page.getByRole("button", { name: "上一页" }).isDisabled();
  await page.getByRole("button", { name: "下一页" }).click();
  await expect(page).toHaveURL(/page=2/);
  await page.goBack();
  await expect(page).toHaveURL(/page=1/);
  await expect(page.getByText("第 1 页")).toBeVisible();
  await page.goForward();
  await expect(page).toHaveURL(/page=2/);
});

test("资料库深链接恢复抽屉状态", async ({ page }) => {
  await installLibraryFixture(page);
  await page.goto("/documents?page=1&pageSize=25&sort=updated_at&order=desc&documentId=7");

  await expect(page.getByRole("dialog", { name: "资料详情" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "在线预览" })).toBeVisible();
  await page.getByRole("button", { name: "关闭资料详情" }).first().click();
  await expect(page).not.toHaveURL(/documentId=7/);
});

for (const [width, height] of [[1536, 960], [1280, 800], [768, 1024], [390, 844]] as const) {
  test(`资料库固定视口 ${width}×${height} 截图`, async ({ page }) => {
    await installLibraryFixture(page);
    await page.setViewportSize({ width, height });
    await page.goto("/documents?page=1&pageSize=25&sort=updated_at&order=desc");
    await expect(page.getByText("资料总量")).toBeVisible();
    await screenshotRegions(page, `${width}x${height}`);
    if (width < 1024) {
      await page.getByRole("button", { name: "资料来源", exact: true }).click();
      await expect(page.getByRole("tree", { name: "资料来源树" })).toBeVisible();
      await page.locator(".source-nav").screenshot({ path: `../docs/frontend-rebuild/screenshots/resource-library/resource-library-${width}x${height}-rail-open.png` });
      await page.getByRole("button", { name: "关闭资料来源" }).click();
    } else await expect(page.getByRole("tree", { name: "资料来源树" })).toBeVisible();
    const viewport = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
      bodyScrollWidth: document.body.scrollWidth,
      overflow: Array.from(document.body.querySelectorAll<HTMLElement>("*")).map((element) => {
        const rect = element.getBoundingClientRect();
        return { tag: element.tagName, className: element.className, right: Math.round(rect.right), width: Math.round(rect.width) };
      }).filter((element) => element.right > window.innerWidth + 1).sort((left, right) => left.right - right.right).slice(0, 12),
    }));
    expect(viewport.scrollWidth, JSON.stringify(viewport)).toBeLessThanOrEqual(viewport.clientWidth);
  });
}

test("资料库空结果反馈", async ({ page }) => {
  await installLibraryFixture(page);
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/documents?page=1&pageSize=25&sort=updated_at&order=desc");
  await page.getByPlaceholder("搜索资料标题、正文内容、路径或来源…").fill("noresult");
  await expect(page.getByText("没有找到符合当前条件的资料。可以清除搜索或筛选后重试。")).toBeVisible();
});

test("资料库处理任务反馈", async ({ page }) => {
  await installLibraryFixture(page);
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/documents?page=1&pageSize=25&sort=updated_at&order=desc");
  await page.getByRole("button", { name: "修复 SGLT2 机制研究笔记.md" }).click();
  await expect(page.getByText("已提交处理任务 #99。")).toBeVisible();
});

test("只有一篇资料时表格与分页紧邻且页面没有横向滚动", async ({ page }) => {
  await installLibraryFixture(page, [resourceItems[0]], 1);
  await page.setViewportSize({ width: 1680, height: 945 });
  await page.goto("/documents?page=1&pageSize=25&sort=updated_at&order=desc");
  await expect(page.locator(".document-table")).toBeVisible();

  const geometry = await page.evaluate(() => {
    const table = document.querySelector(".document-table")?.getBoundingClientRect();
    const pagination = document.querySelector(".pagination")?.getBoundingClientRect();
    return {
      gap: table && pagination ? Math.round(pagination.top - table.bottom) : null,
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    };
  });
  expect(geometry.gap).not.toBeNull();
  expect(geometry.gap ?? 999).toBeLessThanOrEqual(8);
  expect(geometry.scrollWidth).toBeLessThanOrEqual(geometry.clientWidth);
});
