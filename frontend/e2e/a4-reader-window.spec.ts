import { expect, test } from "@playwright/test";

/** 只生成明确标注为合成的 PDF 夹具，浏览器仍运行真实 PDF.js。 */
function syntheticPdf(pageCount: number): Buffer {
  const objects = ["<< /Type /Catalog /Pages 2 0 R >>", "", "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"];
  const kids: number[] = [];
  for (let number = 1; number <= pageCount; number++) {
    const id = objects.length + 1; kids.push(id);
    const content = `BT /F1 18 Tf 50 730 Td (Synthetic A4 page ${number}) Tj ET`;
    objects.push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] /Resources << /Font << /F1 3 0 R >> >> /Contents ${id + 1} 0 R >>`);
    objects.push(`<< /Length ${content.length} >>\nstream\n${content}\nendstream`);
  }
  objects[1] = `<< /Type /Pages /Count ${pageCount} /Kids [${kids.map(id => `${id} 0 R`).join(" ")}] >>`;
  let pdf = "%PDF-1.7\n"; const offsets = [0];
  objects.forEach((object, index) => { offsets.push(Buffer.byteLength(pdf)); pdf += `${index + 1} 0 obj\n${object}\nendobj\n`; });
  const xref = Buffer.byteLength(pdf);
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  pdf += offsets.slice(1).map(offset => `${String(offset).padStart(10, "0")} 00000 n \n`).join("");
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;
  return Buffer.from(pdf);
}

for (const profile of [
  { name: "desktop", viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 },
  { name: "tablet-hidpi", viewport: { width: 1024, height: 768 }, deviceScaleFactor: 2 },
  { name: "narrow-hidpi", viewport: { width: 480, height: 800 }, deviceScaleFactor: 2 },
]) {
test.describe(profile.name, () => {
test.use({ viewport: profile.viewport, deviceScaleFactor: profile.deviceScaleFactor });
test("real PDF.js releases distant pages, restores text and zooms at a remote page", async ({ page, browserName }, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.route("**/a4-synthetic.pdf", route => route.fulfill({ contentType: "application/pdf", body: syntheticPdf(24) }));
  await page.goto("/e2e/a4-reader-harness.html");
  const first = page.locator('.pdf-page[data-page-number="1"]');
  const last = page.locator('.pdf-page[data-page-number="24"]');
  await expect(first.locator(".text-layer")).toContainText("Synthetic A4 page 1");
  const height = await first.evaluate(element => element.getBoundingClientRect().height);
  await expect(page.getByRole("button", { name: "跳转", exact: true })).toBeEnabled();
  await page.getByRole("spinbutton", { name: "页码" }).fill("24");
  await page.getByRole("button", { name: "跳转", exact: true }).click();
  await expect(last.locator(".text-layer")).toContainText("Synthetic A4 page 24");
  await expect.poll(() => first.locator("canvas").evaluate(canvas => canvas.width)).toBe(0);
  expect(await first.evaluate(element => element.getBoundingClientRect().height)).toBe(height);
  await page.getByRole("button", { name: "放大 PDF" }).click();
  await expect(page.locator('.pdf-page[data-page-number="24"] .text-layer')).toContainText("Synthetic A4 page 24");
  await page.getByRole("spinbutton", { name: "页码" }).fill("1");
  await page.getByRole("button", { name: "跳转", exact: true }).click();
  await expect(first.locator(".text-layer")).toContainText("Synthetic A4 page 1");
  await expect.poll(() => last.locator("canvas").evaluate(canvas => canvas.width)).toBe(0);
  const metrics = await page.locator(".pdf-pages").evaluate(root => ({
    canvasCount: [...root.querySelectorAll("canvas")].filter(canvas => canvas.width > 0).length,
    textNodes: root.querySelectorAll(".text-layer span").length,
    estimatedCanvasBytes: [...root.querySelectorAll("canvas")].reduce((bytes, canvas) => bytes + canvas.width * canvas.height * 4, 0),
    userAgent: navigator.userAgent, pixelRatio: devicePixelRatio,
  }));
  expect(metrics.canvasCount).toBeLessThan(8);
  expect(errors).toEqual([]);
  await testInfo.attach("a4-technical-metrics", { body: JSON.stringify({ ...metrics, browserName, profile: profile.name,
    environment: "single host, simulated viewport and DPI; not physical device validation", fixture: "24-page synthetic PDF", pdfjsVersion: "6.2.108" }), contentType: "application/json" });
});
});
}
