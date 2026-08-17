import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import { knowledgeSourcesApi } from "../../api/knowledgeSources";
import KnowledgeSourceForm from "./KnowledgeSourceForm.vue";

vi.mock("../../api/knowledgeSources", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/knowledgeSources")>();
  return { ...actual, knowledgeSourcesApi: { ...actual.knowledgeSourcesApi, browseDirectory: vi.fn() } };
});

const browseDirectory = vi.mocked(knowledgeSourcesApi.browseDirectory);
const mountForm = () => mount(KnowledgeSourceForm, { props: { disabled: false } });

afterEach(() => vi.resetAllMocks());

describe("KnowledgeSourceForm", () => {
  it("uses the native selection result and derives an empty name from the folder", async () => {
    browseDirectory.mockResolvedValue({ path: "H:\\research\\papers" });
    const wrapper = mountForm();
    await wrapper.get(".browse-action").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("H:\\research\\papers");
    expect((wrapper.get("input").element as HTMLInputElement).value).toBe("papers");
  });

  it("keeps the form unchanged when folder selection is cancelled", async () => {
    browseDirectory.mockResolvedValue({ path: null });
    const wrapper = mountForm();
    await wrapper.get(".browse-action").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("尚未选择文件夹");
  });

  it("does not allow saving before a directory has been selected", () => {
    const wrapper = mountForm();
    expect((wrapper.get(".primary-action").element as HTMLButtonElement).disabled).toBe(true);
  });
});
