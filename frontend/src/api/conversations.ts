export interface Citation { id:number; document_id:number; page:number|null; section:string|null; evidence_text:string|null; citation_text:string|null; retrieval_score:number|null }
export interface Message { id:number; role:string; content:string; citations:Citation[] }
export interface Conversation { id:number; document_ids:number[]; title:string|null; messages:Message[] }
const base="/api/v1/conversations";
async function request<T>(path:string,init?:RequestInit):Promise<T>{const response=await fetch(base+path,init);if(!response.ok)throw new Error("问答请求失败");return response.json() as Promise<T>}
export const conversationsApi={create:(ids:number[])=>request<Conversation>("",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({document_ids:ids})}),get:(id:number)=>request<Conversation>(`/${id}`),ask:(id:number,question:string)=>request<Message>(`/${id}/messages`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({question})})};
