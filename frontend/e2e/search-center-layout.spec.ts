import { expect, test, type Page } from "@playwright/test";
import { fixtureForCase, layoutCases, searchCenterFixture, searchCenterValidation } from "../src/views/LiteratureSearch/searchCenter.fixture";
import type { SearchStrategyDraft } from "../src/types/searchStrategy";

test.use({ channel: "msedge", colorScheme: "light", reducedMotion: "reduce" });
const workspaceUrl = "/literature-search/workspace?strategy_id=999";
const viewports = [[1536, 1024], [1440, 900], [1280, 800], [1024, 768], [768, 1024], [390, 844]];

for (const width of [1536, 1920]) {
  test(`reference composition fits ${width}`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 1080 });
    await mockStrategy(page, searchCenterFixture());
    await page.goto(workspaceUrl);
    await expect(page.locator(".strategy-basis")).toBeVisible();
    const box = await geometry(page);
    const sidebar = box.bounds[".sidebar"];
    const basis = box.bounds[".strategy-basis"];
    expect.soft(basis.x - sidebar.width).toBeGreaterThanOrEqual(22);
    expect.soft(basis.x - sidebar.width).toBeLessThanOrEqual(28);
    expect.soft(width - basis.x - basis.width).toBeLessThanOrEqual(28);
    const inset = await page.locator(".question").evaluate((el) => el.getBoundingClientRect().x - el.closest(".strategy-basis")!.getBoundingClientRect().x);
    expect.soft(inset).toBeGreaterThanOrEqual(18);
    expect.soft(box.bounds[".terms-mesh-section"].height).toBeGreaterThanOrEqual(360);
    expect.soft(box.bounds[".strategy-query"].height).toBeLessThanOrEqual(132);
    expect.soft(box.bounds[".strategy-limits"].height).toBeLessThanOrEqual(110);
    await page.screenshot({ path: testInfo.outputPath(`reference-${width}.png`), fullPage: true });
  });
}

test("short search workspace reaches the viewport edge with its action bar", async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 944 });
  await mockStrategy(page, fixtureForCase("sparse"));
  await page.goto(workspaceUrl);
  await expect(page.locator(".strategy-sticky")).toBeVisible();
  const layout = await page.evaluate(() => {
    const workspace = document.querySelector(".literature-workspace")!.getBoundingClientRect();
    const sticky = document.querySelector(".strategy-sticky")!.getBoundingClientRect();
    return { viewportHeight: innerHeight, workspaceBottom: workspace.bottom, stickyBottom: sticky.bottom };
  });
  expect(layout.workspaceBottom).toBeGreaterThanOrEqual(layout.viewportHeight - 1);
  expect(layout.stickyBottom).toBeGreaterThanOrEqual(layout.viewportHeight - 1);
  await expect(page.locator(".coverage-notice")).toContainText("概念覆盖不足");
});

async function mockStrategy(page: Page, strategy: SearchStrategyDraft): Promise<void> {
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/strategies/999")) return route.fulfill({ json: strategy });
    if (url.pathname.endsWith("/strategies/999/versions")) return route.fulfill({ json: [] });
    if (url.pathname.endsWith("/literature-search")) {
      return route.fulfill({ json: { total: 0, offset: 0, limit: 50, items: [] } });
    }
    if (url.pathname.endsWith("/literature-search/history")) {
      return route.fulfill({ json: { total: 0, offset: 0, limit: 100, items: [] } });
    }
    // 未专门模拟的写请求不得到达真实后端。
    if (route.request().method() !== "GET") return route.fulfill({ status: 503, json: { detail: "验收隔离：未配置的写操作" } });
    return route.continue();
  });
}

async function geometry(page: Page) {
  return page.evaluate(() => {
    const root = document.documentElement;
    const selectors = [".sidebar", ".search-center-header", ".journey", ".strategy-basis", ".terms-mesh-section", ".strategy-query", ".strategy-ready", ".strategy-limits", ".strategy-sticky"];
    const bounds = Object.fromEntries(selectors.map((selector) => {
      const element = document.querySelector(selector)!;
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return [selector, { x: rect.x, y: rect.y, width: rect.width, height: rect.height, display: style.display, overflowX: style.overflowX, background: style.backgroundColor }];
    }));
    const overflow = [...document.querySelectorAll(".literature-workspace *")].filter((element) => {
      const rect = element.getBoundingClientRect();
      return rect.width && rect.right > root.clientWidth + 1 && !element.closest(".journey");
    }).map((element) => ({ class: element.className, text: element.textContent?.slice(0, 70) }));
    return { url: location.href, viewport: innerWidth, dpr: devicePixelRatio, scale: visualViewport?.scale, zoom: getComputedStyle(root).zoom, clientWidth: root.clientWidth, scrollWidth: root.scrollWidth, bounds, overflow };
  });
}

for (const [width, height] of viewports) {
  for (const name of layoutCases) {
    test(`${name} fits ${width}`, async ({ page }, testInfo) => {
      await page.setViewportSize({ width, height });
      const errors: string[] = [];
      page.on("pageerror", (error) => errors.push(error.message));
      const strategy = fixtureForCase(name);
      await mockStrategy(page, strategy);
      await page.goto(workspaceUrl);
      await expect(page.locator(".terms-mesh-section")).toBeVisible();
      await page.evaluate(() => document.fonts.ready);
      const report = await geometry(page);
      await testInfo.attach("geometry", { body: JSON.stringify(report, null, 2), contentType: "application/json" });
      await page.screenshot({ path: testInfo.outputPath(`${name}-${width}.png`), fullPage: true });
      expect.soft(report.scrollWidth).toBeLessThanOrEqual(report.clientWidth + 1);
      expect.soft(report.overflow).toEqual([]);
      expect.soft(errors).toEqual([]);
      if (width > 900) await expect(page.locator(".sidebar")).toBeVisible();
      else await expect(page.getByRole("button", { name: "打开导航" })).toBeVisible();
      if (name === "full") {
        await expect(page.locator(".concept-group").first()).toContainText("5 个术语");
      } else if (name === "unknown" || name === "unstructured") {
        await expect(page.locator(".term-area")).toContainText("exposure_future_category");
        await expect(page.locator(".strategy-basis")).not.toContainText("Population");
        await expect(page.locator(".coverage-notice")).toContainText("尚未识别标准概念");
        await expect(page.locator(".coverage-notice")).not.toContainText("当前仅识别到疾病概念");
      }
      if (name !== "full") await expect(page.locator(".strategy-ready")).not.toContainText("检索策略已准备就绪");
      if (name === "empty") await expect(page.locator(".strategy-sticky .execute")).toBeDisabled();
    });
  }
}

test("all terms remain readable after expansion and category counts do not change", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 768 });
  await mockStrategy(page, searchCenterFixture());
  await page.goto(workspaceUrl);
  await page.getByRole("button", { name: "查看全部", exact: true }).click();
  await expect(page.locator(".term-chip")).toHaveCount(11);
  expect(await page.locator(".term-chip").evaluateAll((elements) => elements.every((el) => el.scrollWidth <= el.clientWidth + 1))).toBe(true);
  await expect(page.locator(".concept-group").first()).toContainText("5 个术语");
});

test("blocking field validation disables both execution controls", async ({ page }) => {
  const strategy = searchCenterFixture();
  strategy.validation_state = "stale";
  await mockStrategy(page, strategy);
  await page.route("**/strategies/999/validate", (route) => route.fulfill({ json: { ...searchCenterValidation(strategy), are_field_tags_valid: false, blocking_errors: [{ code: "unsupported_field_tag", message: "不支持的字段标签", severity: "blocking" }] } }));
  await page.goto(workspaceUrl);
  await page.getByRole("button", { name: "验证", exact: true }).click();
  await expect(page.locator(".strategy-ready")).toContainText("检索策略暂不可执行");
  await expect(page.locator(".search-center-header .execute-button")).toBeDisabled();
  await expect(page.locator(".strategy-sticky .execute")).toBeDisabled();
  await expect(page.locator(".strategy-query")).toContainText("不支持的字段标签");
});

test("query edits invalidate validation and count, and cannot execute the old saved query", async ({ page }) => {
  const strategy = searchCenterFixture();
  await mockStrategy(page, strategy);
  let finishSave: (() => void) | undefined;
  let savedQuery = "";
  await page.route("**/strategies/999", async (route) => {
    if (route.request().method() === "PATCH") {
      savedQuery = route.request().postDataJSON().query_text;
      await new Promise<void>((resolve) => { finishSave = resolve; });
      strategy.query_text = savedQuery;
      strategy.fingerprint = "test-fixture-v2";
      strategy.revision += 1;
      strategy.validation_state = "stale";
    }
    await route.fulfill({ json: strategy });
  });
  await page.route("**/strategies/999/validate", (route) => route.fulfill({ json: searchCenterValidation(strategy) }));
  await page.route("**/strategies/999/count?*", (route) => route.fulfill({ json: { count: 42, fingerprint: strategy.fingerprint, source: "pubmed", retrieved_at: "2026-08-31T00:00:00Z" } }));
  await page.goto(workspaceUrl);
  await page.getByRole("button", { name: "验证", exact: true }).click();
  await page.getByRole("button", { name: "刷新数量", exact: true }).click();
  await expect(page.locator(".count")).toContainText("42 篇");
  await page.getByRole("textbox", { name: "PubMed 检索式" }).fill("ILD[tiab]");
  await expect(page.locator(".strategy-ready")).not.toContainText("检索策略已准备就绪");
  await expect(page.locator(".count")).not.toContainText("42 篇");
  await expect(page.locator(".strategy-sticky .execute")).toBeDisabled();
  await expect.poll(() => Boolean(finishSave)).toBe(true);
  finishSave!();
  await expect(page.locator(".strategy-sticky .execute")).toBeEnabled();
  await expect(page.locator(".strategy-ready h2")).toHaveText("检索式待验证");
  expect(savedQuery).toBe("ILD[tiab]");
  await page.getByRole("button", { name: "验证", exact: true }).click();
  await expect(page.locator(".strategy-ready h2")).toHaveText("检索策略已准备就绪");
});

test("cross-page navigation and refresh keep workspace geometry and pixels stable", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await mockStrategy(page, searchCenterFixture());
  await page.goto(workspaceUrl);
  await expect(page.locator(".strategy-basis")).toBeVisible();
  await expect(page.locator('.sidebar .subnav-link[href="/literature-search"]')).toHaveAttribute("aria-current", "page");
  await page.mouse.move(0, 0);
  const initial = await page.locator(".literature-workspace").screenshot({ animations: "disabled" });
  const reports = [];
  for (const path of ["/literature-search/results", "/literature-search/history", "/recommendations", "/sources"]) {
    const destination = page.locator(`.sidebar a[href="${path}"]`);
    if (path === "/sources" && !(await destination.isVisible())) {
      await page.getByRole("button", { name: "展开研究资源二级导航" }).click();
    }
    await destination.click();
    if (path === "/literature-search/results") {
      // 结果入口异步恢复最近一次快照；等待页面完成恢复后才允许返回。
      await expect(page.locator(".results-workspace, .results-index .actions")).toBeVisible();
      await expect(page).toHaveURL(/\/literature-search\/results(?:\/\d+\?.*)?$/);
    } else {
      await expect(page).toHaveURL(new RegExp(`${path}$`));
    }
    await expect(page.locator(".literature-workspace")).toHaveCount(0);
    await expect(page.locator("#main-content")).not.toBeEmpty();
    await page.screenshot({ path: testInfo.outputPath(`route-${path.replaceAll("/", "-")}.png`) });
    await page.goBack();
    await expect(page).toHaveURL(new RegExp(`${workspaceUrl.replace("?", "\\?")}$`));
    await expect(page.locator(".strategy-basis")).toBeVisible();
    await expect(page.locator('.sidebar .subnav-link[href="/literature-search"]')).toHaveAttribute("aria-current", "page");
    await page.mouse.move(0, 0);
    const returned = await page.locator(".literature-workspace").screenshot({ animations: "disabled" });
    expect(returned.equals(initial), `workspace screenshot after ${path}`).toBe(true);
    reports.push({ from: path, geometry: await geometry(page) });
  }
  await page.reload();
  await expect(page.locator(".strategy-basis")).toBeVisible();
  expect((await page.locator(".literature-workspace").screenshot({ animations: "disabled" })).equals(initial)).toBe(true);
  expect(errors).toEqual([]);
  await testInfo.attach("cross-route-geometry", { body: JSON.stringify(reports, null, 2), contentType: "application/json" });
});

test("mobile navigation opens and closes, terms can be added without losing keyboard focus", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockStrategy(page, fixtureForCase("unstructured"));
  await page.goto(workspaceUrl);
  await page.getByRole("button", { name: "打开导航" }).click();
  await expect(page.locator(".drawer nav")).toBeVisible();
  await page.getByRole("button", { name: "关闭导航", exact: true }).click({ position: { x: 380, y: 400 } });
  await expect(page.locator(".drawer")).toHaveCount(0);
  await page.getByRole("button", { name: "添加术语", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("textbox", { name: "添加检索术语" })).toBeFocused();
  await page.getByRole("textbox", { name: "添加检索术语" }).fill("test keyword");
  await page.getByRole("button", { name: "取消", exact: true }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(page.getByRole("button", { name: "添加术语", exact: true })).toBeFocused();
});

test("tablet workspace provides navigation in the shared breakpoint gap", async ({ page }) => {
  await page.setViewportSize({ width: 768, height: 1024 });
  await mockStrategy(page, searchCenterFixture());
  await page.goto(workspaceUrl);
  await page.getByRole("button", { name: "打开导航" }).click();
  await expect(page.getByRole("navigation", { name: "检索中心导航" })).toBeVisible();
  await page.getByRole("navigation", { name: "检索中心导航" }).getByRole("link", { name: "检索结果", exact: true }).click();
  await expect(page.locator(".results-workspace, .results-index .actions")).toBeVisible();
  await expect(page).toHaveURL(/\/literature-search\/results(?:\/\d+\?.*)?$/);
  await page.goBack();
  await expect(page.locator(".strategy-basis")).toBeVisible();
});

test("MeSH not found is not presented as verified even when backend mesh_valid is true", async ({ page }) => {
  const strategy = fixtureForCase("not_found");
  strategy.validation_state = "stale";
  await mockStrategy(page, strategy);
  await page.route("**/strategies/999/validate", (route) => route.fulfill({ json: searchCenterValidation(strategy) }));
  await page.goto(workspaceUrl);
  await page.getByRole("button", { name: "验证", exact: true }).click();
  await expect(page.locator(".strategy-ready")).toContainText("MeSH 未找到");
  await expect(page.locator(".strategy-ready")).not.toContainText("MeSH 已验证");
  await expect(page.locator(".strategy-sticky .execute")).toBeEnabled();
});

test("validation request failures remain visible and retry can recover", async ({ page }) => {
  const strategy = fixtureForCase("unavailable");
  strategy.validation_state = "stale";
  await mockStrategy(page, strategy);
  let calls = 0;
  await page.route("**/strategies/999/validate", (route) => {
    calls += 1;
    return calls === 1
      ? route.fulfill({ status: 503, json: { detail: "测试验证服务暂不可用" } })
      : route.fulfill({ json: { ...searchCenterValidation(strategy), is_mesh_valid: false, warnings: [{ code: "mesh_unavailable", message: "MeSH 暂不可用", severity: "warning" }] } });
  });
  await page.goto(workspaceUrl);
  await page.getByRole("button", { name: "验证", exact: true }).click();
  await expect(page.locator(".strategy-ready [role=alert]")).toContainText("测试验证服务暂不可用");
  await page.getByRole("button", { name: "验证", exact: true }).click();
  await expect(page.locator(".strategy-ready [role=alert]")).toHaveCount(0);
  await expect(page.locator(".strategy-sticky .execute")).toBeEnabled();
  await expect(page.locator(".strategy-query")).toContainText("MeSH 暂不可用");
});
