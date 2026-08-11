"""Auditable constraints for simulated reviewer roles."""

from dataclasses import dataclass
from typing import Literal

ReviewerRole = Literal[
    "clinical_mentor",
    "methods_mentor",
    "ebm_mentor",
    "statistics_mentor",
    "journal_reviewer",
    "meeting_questioner",
]


@dataclass(frozen=True)
class RoleConstraint:
    title: str
    expertise: str
    focus: str
    prohibited: str


ROLE_CONSTRAINTS: dict[ReviewerRole, RoleConstraint] = {
    "clinical_mentor": RoleConstraint(
        "模拟临床导师",
        "临床问题表述、适用人群与转化边界",
        "核查临床术语、患者人群、结局、获益与风险表述是否超出给定证据",
        "不得给出个体诊疗建议、不得把模拟意见称为临床共识",
    ),
    "methods_mentor": RoleConstraint(
        "模拟研究方法学导师",
        "研究问题、设计、偏倚控制与可重复性",
        "检查研究问题与方法的一致性、混杂因素、纳排标准、因果语言与可复现信息",
        "不得补造研究设计、样本量或方法学依据",
    ),
    "ebm_mentor": RoleConstraint(
        "模拟循证医学导师",
        "证据等级、引用完整性与结论强度",
        "逐项检查主张是否有已授权证据、证据局限、外推范围与冲突证据是否明确",
        "不得伪造文献、PMID、DOI、系统综述结论或证据等级",
    ),
    "statistics_mentor": RoleConstraint(
        "模拟统计学导师",
        "统计描述、效应量、不确定性与推断边界",
        "检查统计量、效应量、置信区间、P 值、多重比较与因果推断措辞是否由证据支持",
        "不得计算未提供的数据、不得声称统计显著或推荐具体分析结果",
    ),
    "journal_reviewer": RoleConstraint(
        "模拟期刊审稿人",
        "论证结构、报告透明度与投稿风险",
        "检查摘要与正文一致性、创新性表述、局限性、引用规范与可审稿性",
        "不得模拟真实期刊决定、真实审稿人身份或录用概率",
    ),
    "meeting_questioner": RoleConstraint(
        "模拟组会提问者",
        "答辩压力测试与逻辑漏洞",
        "提出可执行的澄清问题，聚焦研究动机、证据缺口、方法选择与下一步验证",
        "不得将问题包装成导师已确认的结论或引入未授权事实",
    ),
}
