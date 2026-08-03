export type CellSource = "model" | "human" | "missing";
export interface PrototypePaper { id: string; title: string; studyType: string; }
export interface PrototypeField { id: string; label: string; }
export interface PrototypeCell { value: string; source: CellSource; note?: string; }
export const prototypePapers: PrototypePaper[] = [{ id:"a", title:"演示论文 A", studyType:"研究类型未提供" }, { id:"b", title:"演示论文 B", studyType:"研究类型未提供" }, { id:"c", title:"演示论文 C", studyType:"研究类型未提供" }];
export const prototypeFields: PrototypeField[] = ["研究类型","对象","样本量","方法","干预或暴露","对照","结局","主要结果","创新","局限"].map((label, index) => ({ id:`f${index}`, label }));
export function prototypeCell(field: PrototypeField, paper: PrototypePaper): PrototypeCell { return field.label === "研究类型" ? { value: paper.studyType, source:"missing" } : { value:"原型数据：待真实多论文处理接入", source:"missing" }; }
