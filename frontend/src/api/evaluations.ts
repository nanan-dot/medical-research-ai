import { apiRequest } from "./client";
export interface EvaluationRun { id:number; dataset_version:string; status:string; created_at:string }
export const evaluationsApi = {
  create: (datasetVersion:string, promptVersion:string) => apiRequest<EvaluationRun>("/evaluations", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({dataset_version:datasetVersion,prompt_version:promptVersion,retriever_config:{},model_config:{}})}),
  get: (id:number) => apiRequest<EvaluationRun>(`/evaluations/${id}`),
};
