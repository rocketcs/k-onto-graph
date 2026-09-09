import { locale } from "./i18n";

// Translate built-in display terms without changing graph data or API identifiers.
const DISPLAY_TERMS: Record<string, string> = {
  entity: "实体", biomolecule: "生物分子", condition: "病症", compound: "化合物",
  process: "过程", community: "社群", protein: "蛋白质", gene: "基因",
  disease: "疾病", drug: "药物", pathway: "通路", document: "文档",
  person: "人物", organization: "组织", concept: "概念", memory: "记忆",
  agentmemory: "智能体记忆", chunk: "文本片段", topic: "主题",
  category: "类别", decision: "决策", decision_maker: "决策者", location: "地点", project: "项目",
  direct: "直接", near: "近距离", "mid-range": "中距离", distant: "远距离",
  off: "关闭", ego: "自我中心网络", heatmap: "热力图", structural: "结构距离",
  semantic: "语义距离", overview: "概览", mid: "中景", detail: "细节",
  exact: "精确", family: "同组", aggregate: "聚合", aggregated: "聚合",
};

export function exploreTerm(value: string): string {
  return locale === "zh-CN" ? DISPLAY_TERMS[value.toLowerCase()] ?? value : value;
}
