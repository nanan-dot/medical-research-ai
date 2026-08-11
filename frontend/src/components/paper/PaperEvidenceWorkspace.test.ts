import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";

import PaperEvidenceWorkspace from "./PaperEvidenceWorkspace.vue";

const document = { id: 42, original_filename: "真实论文.pdf", file_path: "papers/real.pdf", parse_status: "succeeded", index_status: "succeeded", paperqa_index_key: "index-42", knowledge_source_id: 1, media_type: "application/pdf", file_hash: "hash", file_size: 1, modified_time: "2026-01-01", scan_state: "pending", error_code: null, error_message: null, retry_count: 0, started_at: null, finished_at: null, parsed_is_scanned: false } as const;
const citation = { id: 8, document_id: 42, page: 7, section: "Methods", citation_text: "真实返回的引用", evidence_text: "真实返回的证据摘录", retrieval_score: null };
const conversation = { id: 5, document_ids: [42], title: null, research_context_id: null, messages: [{ id: 1, role: "user", content: "真实问题", citations: [] }, { id: 2, role: "assistant", content: "真实回答", answer_status: "answered", citations: [citation] }] };
function response(body: unknown, status = 200): Response { return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }); }
function mountWorkspace() { return mount(PaperEvidenceWorkspace, { props: { document, canCreate: true } }); }

afterEach(() => vi.restoreAllMocks());

test("通过 latest 恢复当前论文的真实会话，并展示真实引用字段", async () => {
  const fetchMock = vi.fn((input: RequestInfo | URL) => Promise.resolve(String(input).includes("/latest?") ? response(conversation) : response([{ id: 5, document_ids: [42], title: null, research_context_id: null, updated_at: "2026-01-01", message_count: 2 }])));
  vi.stubGlobal("fetch", fetchMock);
  const wrapper = mountWorkspace(); await flushPromises();
  expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/conversations/latest?document_id=42"), undefined);
  expect(wrapper.text()).toContain("真实论文.pdf"); expect(wrapper.text()).toContain("真实返回的引用"); expect(wrapper.text()).toContain("章节：Methods"); expect(wrapper.text()).toContain("页码：7"); expect(wrapper.text()).toContain("真实问题");
});

test("无会话时显示真实创建引导，不渲染演示论文或伪造引用", async () => {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => Promise.resolve(String(input).includes("/latest?") ? response({ detail: "not found" }, 404) : response([]))));
  const wrapper = mountWorkspace(); await flushPromises();
  expect(wrapper.text()).toContain("尚无与当前论文关联的问答会话"); expect(wrapper.text()).toContain("创建问答会话"); expect(wrapper.text()).not.toContain("演示论文"); expect(wrapper.find(".citation-card").exists()).toBe(false);
});

test("证据不足和缺失定位字段使用真实状态与未提供文案", async () => {
  const insufficient = { ...conversation, messages: [{ id: 3, role: "assistant", content: "系统返回", answer_status: "insufficient_evidence", citations: [{ ...citation, page: null, section: null, evidence_text: null, citation_text: null }] }] };
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => Promise.resolve(String(input).includes("/latest?") ? response(insufficient) : response([]))));
  const wrapper = mountWorkspace(); await flushPromises();
  expect(wrapper.text()).toContain("证据不足 / 需人工核对"); expect(wrapper.text()).toContain("未提供");
});

test("会话请求失败显示错误，不回退为成功界面", async () => {
  vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(response({ detail: "会话服务不可用" }, 500))));
  const wrapper = mountWorkspace(); await flushPromises();
  expect(wrapper.text()).toContain("会话服务不可用"); expect(wrapper.text()).not.toContain("真实回答");
});

test("发送问题调用真实 API，pending 时阻止重复提交", async () => {
  let resolveAsk: ((value: Response) => void) | undefined;
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/latest?")) return Promise.resolve(response(conversation));
    if (url.endsWith("/messages")) return new Promise<Response>((resolve) => { resolveAsk = resolve; });
    if (url.endsWith("/conversations/5")) return Promise.resolve(response(conversation));
    return Promise.resolve(response([]));
  });
  vi.stubGlobal("fetch", fetchMock);
  const wrapper = mountWorkspace(); await flushPromises();
  await wrapper.get("textarea").setValue("新问题");
  await wrapper.get("form").trigger("submit"); await wrapper.get("form").trigger("submit");
  expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/messages"))).toHaveLength(1);
  resolveAsk?.(response({ id: 3, role: "assistant", content: "回答", citations: [] })); await flushPromises();
});

test("keeps the create API response as the active conversation", async () => {
  const created = { ...conversation, id: 9, messages: [] };
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("/latest?")) return Promise.resolve(response({ detail: "not found" }, 404));
    if (url.endsWith("/conversations") && init?.method === "POST") return Promise.resolve(response(created));
    return Promise.resolve(response([]));
  });
  vi.stubGlobal("fetch", fetchMock);
  const wrapper = mountWorkspace(); await flushPromises();
  await wrapper.get(".no-conversation button").trigger("click"); await flushPromises();
  expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/conversations"), expect.objectContaining({ method: "POST" }));
  expect(wrapper.find(".no-conversation").exists()).toBe(false);
  expect(wrapper.get("textarea").attributes("disabled")).toBeUndefined();
});

test("clears a selected citation when its document changes", async () => {
  const fetchMock = vi.fn((input: RequestInfo | URL) => Promise.resolve(String(input).includes("/latest?") ? response(conversation) : response([])));
  vi.stubGlobal("fetch", fetchMock);
  const wrapper = mountWorkspace(); await flushPromises();
  await wrapper.get(".citation-card").trigger("click");
  expect(wrapper.find(".selected-source").exists()).toBe(true);
  await wrapper.setProps({ document: { ...document, id: 43, original_filename: "another-live-paper.pdf" } }); await flushPromises();
  expect(wrapper.find(".selected-source").exists()).toBe(false);
});
