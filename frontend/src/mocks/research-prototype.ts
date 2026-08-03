import type { DirectionCandidate, PresentationDraft, ResearchCondition, WritingProject } from "../types/research-prototype";

export const researchConditions: ResearchCondition[] = [
  ["specialty", "专业", "待导师确认"], ["advisor", "导师方向", "待导师确认"], ["topic", "兴趣主题", "未填写"], ["study", "研究类型", "待导师确认"],
  ["sample", "样本", "不知道"], ["data", "数据", "不知道"], ["equipment", "设备", "不知道"], ["method", "技术", "待导师确认"],
  ["time", "时间", "未填写"], ["budget", "预算", "不知道"], ["ethics", "伦理", "待确认"], ["collaboration", "合作条件", "待导师确认"],
].map(([id, label, value]) => ({ id, label, value, status: "unknown" }));

export const directionCandidates: DirectionCandidate[] = [
  { id: "d1", title: "候选方向 A：待界定的临床研究问题", question: "需由研究者与导师共同明确问题边界。", evidence: "论文证据尚未接入，不生成文献结论。", controversy: "争议点待后续检索与导师讨论。", feasibility: "条件信息不完整，暂不能评估。", risk: "样本、伦理、时间和数据条件均待确认。", searchNext: "先补充研究对象与可获得资源。", advisorCheck: "确认研究问题、样本与伦理路径。" },
  { id: "d2", title: "候选方向 B：待界定的方法学习方向", question: "需确认可学习的方法与使用场景。", evidence: "当前为前端原型，不含真实方法学证据。", controversy: "适用范围待检索后比较。", feasibility: "设备与技术支持信息未知。", risk: "培训周期、预算和合作条件待确认。", searchNext: "记录导师建议后再建立检索式。", advisorCheck: "确认技术可及性与培训安排。" },
  { id: "d3", title: "候选方向 C：待界定的课题讨论方向", question: "仅作为讨论起点，不是最终决策。", evidence: "无已验证文献依据。", controversy: "需要明确不同方案的取舍。", feasibility: "无法在条件未知时给出判断。", risk: "避免将未知信息自动补全为结论。", searchNext: "补充约束条件并进行持续检索。", advisorCheck: "确定是否进入开题讨论。" },
];

export const presentationTypes = ["单篇论文汇报", "多篇文献专题汇报", "课题进展汇报", "开题或方向讨论", "方法学习汇报"];
export const presentationDrafts: PresentationDraft[] = [
  { id: "p1", title: "未命名组会草稿", type: "开题或方向讨论", progress: "结构待完善", evidenceStatus: "MOCK / 未接入", pending: "确认研究条件", updatedAt: "本地原型" },
  { id: "p2", title: "方法学习汇报草稿", type: "方法学习汇报", progress: "待开始", evidenceStatus: "MOCK / 未接入", pending: "选择学习材料", updatedAt: "本地原型" },
];

export const writingProjects: WritingProject[] = [
  { id: "w1", title: "综述提纲草稿", type: "综述提纲", version: "本地 v0", updatedAt: "未接入", origin: "用户" },
  { id: "w2", title: "开题提纲草稿", type: "开题提纲", version: "本地 v0", updatedAt: "未接入", origin: "待确认" },
];
