// visual-test-only capture runner. Production source never imports its fixture.
import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import WebSocket from "ws";
import { workspaceStrategyFixture as strategy } from "./visual-test-only/workspace-v2.fixture.mjs";

const edge = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const output = "D:\\AI_project\\rag_medicine\\docs\\frontend-rebuild\\screenshots\\literature-search-workspace-v2";
const baseUrl = process.env.WORKSPACE_CAPTURE_URL ?? "http://127.0.0.1:5173";
const viewports = [[1536,1024],[1440,900],[1280,800],[1024,768],[768,1024],[390,844]];
const selectors = [
  ".search-center-header",
  ".journey",
  ".strategy-basis",
  ".terms-mesh-section",
  ".strategy-query",
  ".strategy-limits",
  ".strategy-ready",
  ".strategy-sticky",
];
const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

async function target(port) { for (let i=0;i<30;i+=1) { try { const pages=await (await fetch(`http://127.0.0.1:${port}/json`)).json(); const page=pages.find((item)=>item.type==="page"&&(item.url==="about:blank"||item.url.startsWith("http"))); if (page?.webSocketDebuggerUrl) return page; } catch {} await sleep(150); } throw new Error("Edge DevTools unavailable"); }
function command(socket, id, method, params={}) { return new Promise((resolve,reject)=>{ const listener=(raw)=>{ const message=JSON.parse(raw); if(message.id!==id.value)return; socket.off("message",listener); if (message.error) { reject(new Error(message.error.message)); return; } resolve(message.result); }; socket.on("message",listener); socket.send(JSON.stringify({id:++id.value,method,params})); }); }
function fixtureFor(url) { if (url.includes("/versions")) return strategy.versions; if (url.includes("/literature-search?")) return {items:[],total:0,offset:0,limit:50}; return strategy; }
async function capture(width,height) {
 const port=9333; const browser=spawn(edge,["--headless=new","--disable-gpu","--force-device-scale-factor=1",`--remote-debugging-port=${port}`,"about:blank"],{windowsHide:true});
 try { const page=await target(port); const socket=new WebSocket(page.webSocketDebuggerUrl); await new Promise((resolve,reject)=>{socket.once("open",resolve);socket.once("error",reject)}); const id={value:0}; const c=(m,p)=>command(socket,id,m,p); const errors=[];
 socket.on("message", async raw=>{const m=JSON.parse(raw); if(m.method==="Fetch.requestPaused"){const body=Buffer.from(JSON.stringify(fixtureFor(m.params.request.url))).toString("base64"); await c("Fetch.fulfillRequest",{requestId:m.params.requestId,responseCode:200,responseHeaders:[{name:"Content-Type",value:"application/json"}],body});} if(m.method==="Runtime.exceptionThrown")errors.push(m.params.exceptionDetails.text);});
 await c("Page.enable"); await c("Runtime.enable"); await c("Fetch.enable",{patterns:[{urlPattern:"*://*/api/v1/literature-search*",requestStage:"Request"}]}); await c("Emulation.setDeviceMetricsOverride",{width,height,deviceScaleFactor:1,mobile:false}); await c("Emulation.setEmulatedMedia",{media:"screen",features:[{name:"prefers-color-scheme",value:"light"},{name:"prefers-reduced-motion",value:"reduce"}]}); await c("Emulation.setPageScaleFactor",{pageScaleFactor:1}); await c("Page.navigate",{url:`${baseUrl}/literature-search/workspace?strategy_id=999`});
 for(let i=0;i<50;i+=1){const r=await c("Runtime.evaluate",{expression:`(${JSON.stringify(selectors)}).every(s=>document.querySelector(s))&&document.fonts.status==='loaded'`,returnByValue:true});if(r.result?.value)break;if(i===49){const state=await c("Runtime.evaluate",{expression:"({url:location.href,text:document.body.innerText.slice(0,500)})",returnByValue:true});throw new Error(`workspace locators unavailable: ${JSON.stringify(state.result?.value)}`)}await sleep(100);}
 await c("Runtime.evaluate",{expression:"window.scrollTo(0, 0)"});
 await sleep(250);
 const geometry=await c("Runtime.evaluate",{expression:`({environment:{devicePixelRatio:window.devicePixelRatio,visualViewportScale:window.visualViewport?.scale??1,scrollX:window.scrollX,scrollY:window.scrollY,fontsStatus:document.fonts.status,colorScheme:matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light',zoom:getComputedStyle(document.documentElement).zoom||'1'},typography:Object.fromEntries(${JSON.stringify(selectors)}.map(s=>{const e=document.querySelector(s),style=getComputedStyle(e);return[s,{fontFamily:style.fontFamily,fontSize:style.fontSize,lineHeight:style.lineHeight,fontWeight:style.fontWeight,backgroundColor:style.backgroundColor,color:style.color,borderRadius:style.borderRadius}]})),anchors:Object.fromEntries(${JSON.stringify(selectors)}.map(s=>{const r=document.querySelector(s).getBoundingClientRect();return[s,{x:r.x,y:r.y,width:r.width,height:r.height}]})),document:{clientHeight:document.documentElement.clientHeight,scrollHeight:document.documentElement.scrollHeight,clientWidth:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth},overflowing:[...document.querySelectorAll('*')].filter(e=>e.scrollWidth>e.clientWidth+1).map(e=>({tag:e.tagName,class:e.className,clientWidth:e.clientWidth,scrollWidth:e.scrollWidth})).slice(0,20),offscreenRight:[...document.querySelectorAll('*')].map(e=>{const r=e.getBoundingClientRect();return{tag:e.tagName,class:e.className,right:Math.round(r.right),width:Math.round(r.width)}}).filter(e=>e.right>document.documentElement.clientWidth+1).slice(0,20),children:[...document.querySelector('.literature-workspace').children].map(e=>{const r=e.getBoundingClientRect();return{class:e.className,y:r.y,height:r.height}})})`,returnByValue:true}); const shot=await c("Page.captureScreenshot",{format:"png"}); await writeFile(`${output}/workspace-${width}x${height}.png`,Buffer.from(shot.data,"base64")); socket.close(); if(errors.length)throw new Error(errors.join(";")); return {viewport:`${width}x${height}`,geometry:geometry.result.value};
 } finally { browser.kill(); }
}
await mkdir(output,{recursive:true}); const reports=[]; for(const [w,h] of viewports)reports.push(await capture(w,h)); await writeFile(`${output}/geometry-report.json`,JSON.stringify({visualTestOnly:true,reports},null,2));
