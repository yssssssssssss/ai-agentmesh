#!/usr/bin/env python3
"""Create an editable investor deck by reusing the existing TwinMesh PPT layout."""

from __future__ import annotations

import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "deliverables/twinmesh-hackathon/TwinMesh-hackathon-roadshow.pptx"
TARGET = ROOT / "deliverables/bbs-collaboration-roadshow/AgentMesh-BBS-协作图投资路演.pptx"
TEXT_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}t"


SLIDES = [
    [
        "01",
        "ENTERPRISE COLLABORATION RUNTIME",
        "AgentMesh",
        "让企业 Agent 协作可验证、可治理、可复用",
        "以协作黑板 BBS 记录任务事实，以协作图解释工作过程。让研究、数据、风险和项目知识围绕同一目标协同。",
        "任务协作", "证据账本", "过程可解释", "组织记忆",
    ],
    [
        "02",
        "企业已经拥有 AI，却仍缺少可信的协作机制",
        "不是模型不够，而是任务、工具结果、责任和决策没有进入同一条可验证链路。",
        "上下文断裂", "项目背景散落在聊天、文档、数据系统与个人经验中。",
        "重复协同", "人不断转述背景、找资料、催确认、汇总结论。",
        "结果不可核验", "AI 回答没有来源和责任边界，难以进入正式流程。",
        "经验无法复用", "项目结束后，证据和决策没有沉淀为下一次工作的输入。",
    ],
    [
        "03",
        "产品定义：企业 Agent 的可信协作运行时",
        "以任务为单位，把人、Agent、工具与证据组织成一个可推进、可复核的协作闭环。",
        "任务", "目标、负责人、完成条件、执行状态和风险边界。",
        "协作黑板", "request、evidence、risk、decision、handoff 等结构化事件。",
        "协作图", "谁参与、谁负责、卡在哪里、证据从何而来，一眼可见。",
    ],
    [
        "04",
        "BBS：不是论坛，是 Agent 之间的证据与责任账本",
        "任务请求", "个人 Agent 在知识不足时创建 request，声明目标、负责人和完成条件。",
        "证据与风险", "research、data、document 提交 evidence；可疑外部内容隔离，高风险动作进入 Inbox。",
        "结构化交接", "handoff 明确当前结果、阻塞点、下一负责人和完成标准，并保留来源、权限和时间。",
        "把协作从难以追溯的聊天记录，转化为企业能够核验和管理的任务事实。",
    ],
    [
        "05",
        "当前闭环：从用户目标到带来源的协作结果",
        "AI-native 的关键不是自由聊天，而是让 Agent 在任务、权限、证据和停止条件内连续推进。",
        "1", "用户发起", "从 Chat 或业务入口提出检索、数据、风险或文档目标。",
        "2", "创建任务", "Task 与 BBS request 记录协作目标、参与者和完成条件。",
        "3", "能力执行", "research、data、risk Agent 在已授权工具范围内取证或审查。",
        "4", "风险治理", "外部资料在进入模型合成前检查；高风险行为转人工确认。",
        "5", "结果沉淀", "带来源结果返回用户，并可提升为候选项目或团队记忆。",
        "治理底座", "权限、工具授权、来源、风险策略、人审和审计日志贯穿全流程。",
    ],
    [
        "06",
        "协作图：把黑箱 Agent 执行变成可解释的任务地图",
        "任务泳道", "按 Task 聚合 request、evidence、risk、handoff 与当前协作阶段。",
        "责任与关系", "显示当前 owner、执行锁、上下游参与者和关联事件，解释证据、修正、决策和交接。",
        "管理可行动", "流程图和时间线帮助负责人快速发现等待外部能力、风险隔离和待人工确认任务。",
        "协作图的价值不是展示炫技，而是把每个任务的状态、责任与阻塞转化为可行动的信息。",
    ],
    [
        "07",
        "一个可演示的协作闭环：知识不足时，系统自动补证",
        "当前原型已跑通 request -> evidence -> 风险隔离或合成回复的受控闭环。",
        "1", "提出问题", "用户查询项目经验，个人 Agent 先检索可见记忆。",
        "2", "发起求助", "记忆不足时创建 BBS request，任务进入等待外部 Agent。",
        "3", "补充证据", "research_agent 获取资料，返回带来源的 evidence 回帖。",
        "4", "风险检查", "可疑内容隔离审核，安全证据才能参与最终回答。",
        "5", "回流复用", "任务完成、协作图更新，高价值结果可生成记忆候选。",
        "任务卡、BBS、锁、交接、派发、风险隔离和协作图已具备；通用多 Agent DAG 是下一阶段。",
    ],
    [
        "08",
        "产品价值：让每一次 AI 协作留下可复用的组织资产",
        "减少协同成本", "减少重复解释、跨角色信息搬运和结果追问。",
        "提高结果可信度", "每个结论可追到来源、执行者、风险状态和确认记录。",
        "缩短问题闭环", "任务状态、负责人和阻塞原因可见，人工介入只出现在需要判断的节点。",
        "沉淀项目记忆", "证据与决策进入候选记忆，确认后反哺下一次项目任务。",
    ],
    [
        "09",
        "竞争格局：平台正在做 Agent，缺的是项目协作的可信执行层",
        "企业搜索", "Glean", "企业上下文与 Agent builder", "项目协作证据链与记忆候选",
        "办公套件", "Copilot Studio", "M365 集成与低代码编排", "异构项目能力的协作协议",
        "业务平台", "Agentforce / ServiceNow", "CRM、ITSM 与流程自动化", "知识密集团队的项目任务闭环",
    ],
    [
        "10",
        "差异化：从“调用 Agent”走向“治理协作结果”",
        "维度", "通用 Agent 平台", "AgentMesh 协作运行时",
        "核心对象", "Agent、工具或工作流", "Task、证据、风险、决策与交接",
        "协作过程", "偏向编排执行", "结构化事件账本 + 责任链 + 协作图",
        "结果可信度", "依赖各平台的治理能力", "来源优先、外部内容隔离、审批和审计内建",
        "知识沉淀", "通常聚焦检索或单次自动化", "协作结果可提升为候选项目或团队记忆",
        "产品定位", "通用平台或既有业务域 Agent", "企业 Agent 的可信项目协作层",
    ],
    [
        "11",
        "路线：先验证高价值闭环，再逐步放开自治",
        "阶段一：试点闭环", "研究、数据、风险三类能力接入真实只读数据，验证来源覆盖率、任务时长和人工介入率。",
        "阶段二：协作运行时", "WorkItem、AgentRun、可靠投递、幂等、超时、重试和预算上限，支撑可恢复执行。",
        "阶段三：受控协作", "模板化并行任务与受 schema 限制的 LLM 计划，默认 assisted，按风险分级开放。",
        "阶段四：平台化", "对接更多企业系统和 Agent 平台，形成项目协作与组织记忆基础设施。",
        "投资重点：验证从“可演示协作”到“真实业务任务闭环”的数据飞轮，而不是追求无边界自治。",
    ],
    [
        "12",
        "AgentMesh 让企业 AI 从单点回答走向可验证的协作能力。",
        "协作黑板记录事实，协作图解释过程，任务运行时让人、工具与 Agent 在治理边界内持续推进。",
        "可信协作", "任务驱动", "组织复利",
    ],
]


def replace_slide_text(xml_bytes: bytes, lines: list[str]) -> bytes:
    root = ET.fromstring(xml_bytes)
    nodes = root.findall(f".//{TEXT_NS}")
    if len(nodes) != len(lines):
        raise ValueError(f"Expected {len(lines)} text nodes, found {len(nodes)}")
    for node, value in zip(nodes, lines, strict=True):
        node.text = value
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def main() -> int:
    if not SOURCE.exists():
        print(f"Missing source deck: {SOURCE}", file=sys.stderr)
        return 1
    shutil.copyfile(SOURCE, TARGET)
    with zipfile.ZipFile(TARGET, "r") as source_zip:
        files = {name: source_zip.read(name) for name in source_zip.namelist()}
    for index, lines in enumerate(SLIDES, start=1):
        path = f"ppt/slides/slide{index}.xml"
        files[path] = replace_slide_text(files[path], lines)
    with zipfile.ZipFile(TARGET, "w", compression=zipfile.ZIP_DEFLATED) as target_zip:
        for name, payload in files.items():
            target_zip.writestr(name, payload)
    print(TARGET)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
