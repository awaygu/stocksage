"""DAG 模板与 Planner 测试。

- build_plan: 纯规则,验证各意图生成的 DAG 拓扑与依赖正确。
- validate_plan: 校验逻辑。
- PlannerAgent: 注入会失败的 LLM,强制走 fallback 规则路径,验证端到端计划生成。
"""

import pytest

from backend.agents.router import PlannerAgent
from backend.graph.router import build_plan, validate_plan
from backend.graph.state import StockSageState


class _FailingLLM:
    """总是抛异常的假 LLM,强制 Planner 走 fallback 路径(模拟生产无 API key 场景)。"""

    async def ainvoke(self, messages, **kwargs):
        raise RuntimeError("test: no real LLM")

    def bind(self, **kwargs):
        return self


# ============ build_plan 纯规则测试 ============

def test_price_query_dag_minimal():
    """price_query 应生成 market_data -> report 的最小链路。"""
    plan = build_plan("price_query", ["600519"], ["CN"])
    assert [t["agent"] for t in plan["tasks"]] == ["market_data", "report"]
    assert plan["tasks"][0]["depends_on"] == []
    assert plan["tasks"][1]["depends_on"] == ["T1"]
    assert plan["intent_type"] == "price_query"


def test_comprehensive_research_dag_parallel():
    """comprehensive_research 应有 market_data 扇出 + report 汇合。"""
    plan = build_plan("comprehensive_research", ["002594"], ["CN"])
    agents = [t["agent"] for t in plan["tasks"]]
    assert agents == ["market_data", "technical", "fundamental", "news", "report"]
    # market_data 无依赖
    assert plan["tasks"][0]["depends_on"] == []
    # technical/fundamental/news 都依赖 market_data(T1)
    for t in plan["tasks"][1:4]:
        assert t["depends_on"] == ["T1"]
    # report 依赖三个分析任务(T2,T3,T4) - 隐式 join
    report_task = plan["tasks"][-1]
    assert set(report_task["depends_on"]) == {"T2", "T3", "T4"}
    assert report_task["agent"] == "report"


def test_technical_analysis_dag():
    """technical_analysis: market_data -> technical -> report。"""
    plan = build_plan("technical_analysis", ["000001"], ["CN"])
    assert [t["agent"] for t in plan["tasks"]] == ["market_data", "technical", "report"]
    assert plan["tasks"][1]["depends_on"] == ["T1"]


def test_chat_dag_only_report():
    """chat 意图应只有 report 一个任务。"""
    plan = build_plan("chat", [], ["CN"])
    assert len(plan["tasks"]) == 1
    assert plan["tasks"][0]["agent"] == "report"


def test_unknown_intent_falls_back_to_report():
    """未知意图应回退到单 report 任务。"""
    plan = build_plan("unknown_xyz", [], ["CN"])
    assert len(plan["tasks"]) == 1
    assert plan["tasks"][0]["agent"] == "report"


def test_all_plans_are_valid():
    """所有意图生成的 DAG 应通过 validate_plan 校验。"""
    intents = [
        "price_query", "technical_analysis", "fundamental_analysis",
        "news_analysis", "comprehensive_research", "risk_assessment",
        "industry_comparison", "macro_analysis", "chat", "unknown",
    ]
    for it in intents:
        plan = build_plan(it, ["600519"], ["CN"])
        errors = validate_plan(plan)
        assert errors == [], f"意图 {it} 的计划非法: {errors}"


def test_validate_plan_detects_bad_agent():
    """validate_plan 应检测未知 agent。"""
    plan = build_plan("price_query", ["600519"], ["CN"])
    plan["tasks"][0]["agent"] = "nonexistent_agent"
    errors = validate_plan(plan)
    assert any("未知 agent" in e for e in errors)


def test_validate_plan_detects_missing_dependency():
    """validate_plan 应检测依赖不存在的任务。"""
    plan = build_plan("price_query", ["600519"], ["CN"])
    plan["tasks"][1]["depends_on"] = ["T999"]
    errors = validate_plan(plan)
    assert any("依赖不存在的任务" in e for e in errors)


# ============ PlannerAgent 端到端测试(MockLLM/fallback) ============

def _make_state(query: str) -> StockSageState:
    return {
        "messages": [{"role": "user", "content": query}],
        "current_query": query,
        "session_id": "test-session",
    }


@pytest.mark.asyncio
async def test_planner_price_query_via_fallback():
    """价格类 query 走 fallback 应生成 price_query DAG。

    注入会失败的 LLM,Planner 捕获异常后走 _fallback_intent 规则匹配。
    用带显式代码的 query 测试代码提取;纯名称 query(如"贵州茅台现在多少钱")
    无数字串可提取,stock_codes 为空是预期行为(需 LLM 或名称映射补充)。
    """
    planner = PlannerAgent(llm=_FailingLLM())

    # 带显式代码
    state = _make_state("600519 现在多少钱")
    result = await planner.run(state)
    plan = result["plan"]
    assert plan["intent_type"] == "price_query"
    assert [t["agent"] for t in plan["tasks"]] == ["market_data", "report"]
    assert "600519" in plan["stock_codes"]
    assert result["task_status"]["T1"] == "pending"
    assert result["task_status"]["T2"] == "pending"

    # 纯名称(无数字)走价格意图,代码为空 - 预期行为
    state2 = _make_state("贵州茅台现在多少钱")
    result2 = await planner.run(state2)
    assert result2["plan"]["intent_type"] == "price_query"
    assert result2["plan"]["stock_codes"] == []


@pytest.mark.asyncio
async def test_planner_comprehensive_with_code():
    """带代码的 query 走 fallback 应识别为综合研究。"""
    planner = PlannerAgent(llm=_FailingLLM())
    state = _make_state("全面分析一下 600519")
    result = await planner.run(state)

    plan = result["plan"]
    assert plan["intent_type"] == "comprehensive_research"
    assert "600519" in plan["stock_codes"]
    # 综合研究应有 5 个任务
    assert len(plan["tasks"]) == 5
    # 计划应通过校验
    assert validate_plan(plan) == []


@pytest.mark.asyncio
async def test_planner_chat_no_code():
    """闲聊 query 应生成 chat DAG(单 report)。"""
    planner = PlannerAgent(llm=_FailingLLM())
    state = _make_state("你好")
    result = await planner.run(state)

    plan = result["plan"]
    assert plan["intent_type"] == "chat"
    assert plan["stock_codes"] == []
    assert len(plan["tasks"]) == 1
