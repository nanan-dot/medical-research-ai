import{flushPromises,mount}from"@vue/test-utils";import{afterEach,expect,test,vi}from"vitest";import History from"./History.vue";import{formatSearchChangeNotice}from"./searchChangeNotice";
import { literatureStrategiesApi } from "../../api/literatureStrategies";
const routerStubs={RouterLink:{props:["to"],template:'<a :href="to"><slot /></a>'}};
const execution={id:8,strategy_version_id:4,version:2,result_id:101,status:"succeeded",result_count:3,error_message:null,created_at:"2026-08-05T10:01:00Z"};
const record={id:1,name:"胃癌 EGFR 免疫治疗",research_context_id:null,framework:"PICO",is_pinned:false,is_archived:false,current_version:2,original_query:"胃癌 EGFR 免疫治疗效果如何？",keyword_count:3,mesh_count:1,start_year:2020,end_year:2026,latest_execution:execution};
const detail={...record,database:"pubmed",current_version:{id:4,version:2,original_query:record.original_query,search_string:"gastric cancer AND EGFR",filters:"",model_version:"test",term_groups:["gastric cancer","EGFR","immunotherapy"],mesh_terms:["Stomach Neoplasms"],start_year:2020,end_year:2026,change_summary:{},created_at:"2026-08-05T10:00:00Z"},versions:[],executions:[execution],updated_at:"2026-08-05T10:01:00Z"};
afterEach(()=>vi.unstubAllGlobals());
test("renders persisted strategy metadata and result snapshot",async()=>{const fetchMock=vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({total:1,offset:0,limit:10,items:[record]}))).mockResolvedValueOnce(new Response(JSON.stringify(detail)));vi.stubGlobal("fetch",fetchMock);const wrapper=mount(History,{global:{stubs:routerStubs}});await flushPromises();expect(wrapper.text()).toContain("胃癌 EGFR 免疫治疗");expect(wrapper.text()).toContain("3 关键词");expect(wrapper.text()).toContain("3篇");expect(wrapper.findAll(".history-item")).toHaveLength(1);expect(wrapper.html()).toContain("/literature-search/results/101?from=history");expect((wrapper.get('select[aria-label="检索策略排序方式"]').element as HTMLSelectElement).value).toBe("updated_at");expect(wrapper.find('button[aria-label="列表视图"]').exists()).toBe(false);});
test("removes pin UI and sends backend-wide update and failure filters",async()=>{vi.useFakeTimers();const fetchMock=vi.fn().mockResolvedValue(new Response(JSON.stringify({total:0,offset:0,limit:10,items:[]})));vi.stubGlobal("fetch",fetchMock);const wrapper=mount(History,{global:{stubs:routerStubs}});await flushPromises();expect(wrapper.text()).not.toContain("已置顶");expect(wrapper.find(".star").exists()).toBe(false);await wrapper.get(".quick-filters button:nth-child(2)").trigger("click");await vi.advanceTimersByTimeAsync(300);expect(String(fetchMock.mock.calls.at(-1)?.[0])).toContain("has_changes=true");await wrapper.get(".quick-filters button:nth-child(3)").trigger("click");await vi.advanceTimersByTimeAsync(300);expect(String(fetchMock.mock.calls.at(-1)?.[0])).toContain("execution_status=failed");wrapper.unmount();vi.useRealTimers();});

test("menu is keyboard-accessible and renames through the PATCH API",async()=>{const fetchMock=vi.fn((input:RequestInfo|URL,init?:RequestInit)=>{const url=String(input);if(init?.method==="PATCH")return Promise.resolve(new Response(JSON.stringify({...detail,name:"新名称"})));if(url.includes("/history-strategies/1")&&!url.includes("?"))return Promise.resolve(new Response(JSON.stringify({...detail,name:"新名称"})));if(url.includes("research-contexts"))return Promise.resolve(new Response(JSON.stringify([])));return Promise.resolve(new Response(JSON.stringify({total:1,offset:0,limit:10,items:[record]})));});vi.stubGlobal("fetch",fetchMock);const wrapper=mount(History,{attachTo:document.body,global:{stubs:routerStubs}});await flushPromises();const triggers=wrapper.findAll("button[aria-label='更多策略操作']");expect(new Set(triggers.map(button=>button.attributes("aria-controls"))).size).toBe(triggers.length);const menu=wrapper.find(".history-item button[aria-label='更多策略操作']");await menu.trigger("click");expect(menu.attributes("aria-expanded")).toBe("true");await wrapper.get('[role="menu"]').trigger("keydown",{key:"Escape"});expect(menu.attributes("aria-expanded")).toBe("false");expect(document.activeElement).toBe(menu.element);await menu.trigger("click");await wrapper.get('[role="menuitem"]').trigger("click");await wrapper.get("#strategy-name").setValue("新名称");await wrapper.get("dialog form").trigger("submit");await flushPromises();const patchCall=fetchMock.mock.calls.find((call)=>call[1]?.method==="PATCH");expect(patchCall?.[0]).toContain("/history-strategies/1");expect(String(patchCall?.[1]?.body)).toContain("新名称");wrapper.unmount();});
test("only produces a user-facing notice for meaningful result changes",()=>{expect(formatSearchChangeNotice({previous_count:33,current_count:33,count_delta:0,added_count:0,removed_count:0,added_pmids:[],removed_pmids:[]})).toBeNull();expect(formatSearchChangeNotice({previous_count:33,current_count:35,count_delta:2,added_count:2,removed_count:0,added_pmids:["1","2"],removed_pmids:[]})).toBe("本次检索发现 2 篇新增文献");});

test("management actions call the real move, clone, archive and restore APIs",async()=>{const fetchMock=vi.fn().mockImplementation(()=>Promise.resolve(new Response(JSON.stringify(detail))));vi.stubGlobal("fetch",fetchMock);await literatureStrategiesApi.patch(1,{research_context_id:7});await literatureStrategiesApi.clone(1);await literatureStrategiesApi.archive(1);await literatureStrategiesApi.restore(1);expect(fetchMock.mock.calls.map(call=>[String(call[0]),call[1]?.method])).toEqual(expect.arrayContaining([[expect.stringContaining("/history-strategies/1"),"PATCH"],[expect.stringContaining("/history-strategies/1/clone"),"POST"],[expect.stringContaining("/history-strategies/1/archive"),"POST"],[expect.stringContaining("/history-strategies/1/restore"),"POST"]]));expect(String(fetchMock.mock.calls[0]?.[1]?.body)).toContain('"research_context_id":7');});

test("reruns the selected immutable strategy version and refreshes real snapshots", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ total: 1, offset: 0, limit: 10, items: [record] })))
    .mockResolvedValueOnce(new Response(JSON.stringify(detail)))
    .mockResolvedValueOnce(new Response(JSON.stringify([])))
    .mockResolvedValueOnce(new Response(JSON.stringify(execution), { status: 201 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ total: 1, offset: 0, limit: 10, items: [record] })))
    .mockResolvedValueOnce(new Response(JSON.stringify(detail)));
  vi.stubGlobal("fetch", fetchMock);
  const wrapper = mount(History, { global: { stubs: routerStubs } });
  await flushPromises();
  await wrapper.get(".history-item .rerun").trigger("click");
  await flushPromises();
  const executionCall = fetchMock.mock.calls.find((call) => String(call[0]).includes("/executions"));
  expect(executionCall?.[0]).toContain("/history-strategies/1/versions/2/executions");
  expect(executionCall?.[1]).toEqual(expect.objectContaining({ method: "POST" }));
  expect(fetchMock.mock.calls).toHaveLength(6);
});

test("closing detail does not issue a bogus strategy request", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ total: 1, offset: 0, limit: 10, items: [record] })))
    .mockResolvedValueOnce(new Response(JSON.stringify(detail)))
    .mockResolvedValueOnce(new Response(JSON.stringify([])));
  vi.stubGlobal("fetch", fetchMock);
  const wrapper = mount(History, { attachTo: document.body, global: { stubs: routerStubs } });
  await flushPromises();
  await wrapper.get('button[aria-label="关闭策略详情"]').trigger("click");
  await flushPromises();
  expect(fetchMock).toHaveBeenCalledTimes(3);
  expect(wrapper.text()).toContain("选择一条策略查看版本与执行记录");
  wrapper.unmount();
});

test("shows the specified conflict message when rerun returns 409", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ total: 1, offset: 0, limit: 10, items: [record] })))
    .mockResolvedValueOnce(new Response(JSON.stringify(detail)))
    .mockResolvedValueOnce(new Response(JSON.stringify([])))
    .mockResolvedValueOnce(new Response(JSON.stringify({ error: { code: "conflict", message: "stale" } }), { status: 409 }));
  vi.stubGlobal("fetch", fetchMock);
  const wrapper = mount(History, { global: { stubs: routerStubs } });
  await flushPromises();
  await wrapper.get(".history-item .rerun").trigger("click");
  await flushPromises();
  expect(wrapper.text()).toContain("检索策略已产生新版本，请刷新后重试。");
});

test("exports readable UTF-8 CSV instead of a JSON backup", async () => {
  const blobs: Blob[] = [];
  const createObjectURL = vi.fn((blob: Blob) => {
    blobs.push(blob);
    return "blob:history-export";
  });
  const revokeObjectURL = vi.fn();
  vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
  const fetchMock = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ total: 1, offset: 0, limit: 10, items: [record] })))
    .mockResolvedValueOnce(new Response(JSON.stringify(detail)))
    .mockResolvedValueOnce(new Response(JSON.stringify([])))
    .mockResolvedValueOnce(new Response(JSON.stringify({ exported_at: "2026-08-30T00:00:00Z", total: 1, strategies: [detail] })));
  vi.stubGlobal("fetch", fetchMock);
  const wrapper = mount(History, { global: { stubs: routerStubs } });
  await flushPromises();
  await wrapper.get(".export").trigger("click");
  await flushPromises();
  const blob = blobs[0]!;
  const content = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(blob);
  });
  expect(content).toContain("策略名称");
  expect(content).toContain("胃癌 EGFR 免疫治疗");
  expect(click).toHaveBeenCalled();
});
