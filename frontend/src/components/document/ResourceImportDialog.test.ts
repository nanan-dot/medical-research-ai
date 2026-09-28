import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { resourceLibraryApi } from "../../api/resourceLibrary";
import ResourceImportDialog from "./ResourceImportDialog.vue";

vi.mock("../../api/resourceLibrary", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/resourceLibrary")>();
  return { ...actual, resourceLibraryApi: { ...actual.resourceLibraryApi, imports: vi.fn() } };
});

describe("ResourceImportDialog", () => {
  beforeEach(() => vi.clearAllMocks());

  it("keeps successful and failed files separate in the real import response", async () => {
    vi.mocked(resourceLibraryApi.imports).mockResolvedValue({ items: [
      { original_filename: "ok.pdf", status: "accepted", document_id: 1, task_id: 9, error_code: null, message: null },
      { original_filename: "bad.exe", status: "failed", document_id: null, task_id: null, error_code: "unsupported_format", message: "格式不支持" },
    ] });
    const wrapper = mount(ResourceImportDialog, { props: { open: true }, global: { stubs: { Teleport: true } } });
    const input = wrapper.get('input[type="file"]');
    Object.defineProperty(input.element, "files", { value: [new File(["ok"], "ok.pdf"), new File(["bad"], "bad.exe")] });
    await input.trigger("change");
    await wrapper.get("form").trigger("submit");
    await flushPromises();

    expect(resourceLibraryApi.imports).toHaveBeenCalledWith(expect.arrayContaining([expect.any(File)]));
    expect(wrapper.text()).toContain("上传完成，已进入后台处理任务");
    expect(wrapper.text()).toContain("格式不支持");
    expect(wrapper.get("button.submit").attributes("disabled")).toBeDefined();
  });

  it("explains duplicate PDFs and invalid PDF contents without calling them a generic upload failure", async () => {
    vi.mocked(resourceLibraryApi.imports).mockResolvedValue({ items: [
      { original_filename: "existing.pdf", status: "duplicate", document_id: 3, task_id: null, error_code: "duplicate", message: null },
      { original_filename: "broken.pdf", status: "rejected", document_id: null, task_id: null, error_code: "invalid_pdf_signature", message: null },
    ] });
    const wrapper = mount(ResourceImportDialog, { props: { open: true }, global: { stubs: { Teleport: true } } });
    const input = wrapper.get('input[type="file"]');
    Object.defineProperty(input.element, "files", { value: [new File(["%PDF"], "existing.pdf"), new File(["bad"], "broken.pdf")] });
    await input.trigger("change");
    await wrapper.get("form").trigger("submit");
    await flushPromises();

    expect(wrapper.text()).toContain("资料已存在，无需重复导入");
    expect(wrapper.text()).toContain("PDF 文件内容无效或已损坏");
    expect(wrapper.find(".result-list .duplicate").exists()).toBe(true);
    expect(wrapper.find(".result-list .failed").exists()).toBe(true);
  });
});
