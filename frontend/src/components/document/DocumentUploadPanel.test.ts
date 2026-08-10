import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import DocumentUploadPanel from "./DocumentUploadPanel.vue";

async function selectInputFile(
  wrapper: ReturnType<typeof mount>,
  file: File,
): Promise<void> {
  const input = wrapper.get("input[type=file]").element as HTMLInputElement;
  Object.defineProperty(input, "files", {
    configurable: true,
    value: [file],
  });
  await wrapper.get("input[type=file]").trigger("change");
}

describe("DocumentUploadPanel", () => {
  it("emits a valid PDF selected from the file input", async () => {
    const wrapper = mount(DocumentUploadPanel, {
      props: { uploading: false, errorMessage: null, uploadedFilename: null },
    });
    const pdf = new File(["%PDF-1.7"], "paper.pdf", { type: "application/pdf" });

    await selectInputFile(wrapper, pdf);

    expect(wrapper.emitted("upload")).toEqual([[pdf]]);
  });

  it("shows a local validation error for an invalid selected file", async () => {
    const wrapper = mount(DocumentUploadPanel, {
      props: { uploading: false, errorMessage: null, uploadedFilename: null },
    });
    const textFile = new File(["not a PDF"], "paper.txt", { type: "text/plain" });

    await selectInputFile(wrapper, textFile);

    expect(wrapper.emitted("upload")).toBeUndefined();
    expect(wrapper.text()).toContain("请选择 MIME 类型为 application/pdf 的 PDF 文件。");
  });
});
