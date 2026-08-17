export class ApiError extends Error { constructor(message:string,public readonly status:number,public readonly code?:string){super(message)} }
type ErrorPayload = { error?: { code?: string; message?: string }; detail?: unknown };
function errorMessage(payload: ErrorPayload | null): string {
  if (payload?.error?.message) return payload.error.message;
  if (typeof payload?.detail === "string") return payload.detail;
  if (Array.isArray(payload?.detail)) return "请求参数不符合接口要求";
  return "请求失败";
}
export async function apiRequest<T>(path:string,init?:RequestInit):Promise<T>{const response=await fetch(`/api/v1${path}`,init);if(!response.ok){const payload=await response.json().catch(()=>null) as ErrorPayload|null;throw new ApiError(errorMessage(payload),response.status,payload?.error?.code)}if(response.status===204)return undefined as T;return response.json() as Promise<T>}
