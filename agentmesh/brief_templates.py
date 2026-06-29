from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BriefTemplate:
    id: str
    title: str
    description: str
    keywords: tuple[str, ...]
    sections: tuple[str, ...]
    guidance: str


BRIEF_TEMPLATES: tuple[BriefTemplate, ...] = (
    BriefTemplate(
        id="campaign_homepage",
        title="活动首页改版 Brief",
        description="适用于大促、会场、频道首页和活动页改版。",
        keywords=("首页", "会场", "大促", "618", "双11", "首屏", "入口", "活动页", "改版"),
        sections=("项目背景", "用户需求", "核心结论", "设计目标", "设计原则", "关键模块", "风险与待确认", "来源"),
        guidance="重点关注首屏入口效率、重点商品曝光、转化路径、活动氛围与历史复盘证据。",
    ),
    BriefTemplate(
        id="product_feature",
        title="产品功能 Brief",
        description="适用于功能设计、工具能力、新流程或系统模块。",
        keywords=("功能", "流程", "工具", "系统", "模块", "能力", "后台", "配置"),
        sections=("问题背景", "目标用户", "使用场景", "功能范围", "核心流程", "验收标准", "风险与待确认", "来源"),
        guidance="重点明确目标用户、核心流程、边界范围和可验收结果。",
    ),
    BriefTemplate(
        id="research_summary",
        title="调研分析 Brief",
        description="适用于竞品、相似项目、用户研究和资料分析。",
        keywords=("调研", "竞品", "分析", "相似项目", "资料", "研究", "对比", "参考"),
        sections=("调研问题", "关键发现", "可引用证据", "机会点", "建议方案", "风险与待确认", "来源"),
        guidance="重点保留证据来源、差异判断、可复用经验和下一步建议。",
    ),
)


def select_brief_template(query: str) -> BriefTemplate:
    text = query.lower()
    scored = []
    for template in BRIEF_TEMPLATES:
        score = sum(1 for keyword in template.keywords if keyword.lower() in text)
        scored.append((score, template))
    scored.sort(key=lambda item: item[0], reverse=True)
    if scored and scored[0][0] > 0:
        return scored[0][1]
    return BRIEF_TEMPLATES[0]
