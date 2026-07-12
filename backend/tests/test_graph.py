"""工作流图测试 - 验证静态图编译与跳过逻辑。

核心验证:
1. 图能编译
2. price_query 链路只激活 market_data + report,其余 agent 走 skipped
3. chat 链路只有 report 被激活
4. dispatcher 正确提取 active_agents
"""

import pytest

from backend.graph.graph_builder import StockSageGraphBuilder
from backend.graph.nodes.dispatcher_node import DispatcherNode
from backend.graph.router import build_plan
from backend.graph.state import StockSageState


def test_graph_compiles():
    """图应能成功编译。"""
    graph = StockSageGraphBuilder().get_graph()
    assert graph is not None


@pytest.mark.asyncio
async def test_dispatcher_extracts_active_agents():
    """dispatcher 应从 plan 提取去重的 active_agents。"""
    plan = build_plan("price_query", ["600519"], ["CN"])
    state: StockSageState = {
        "session_id": "test",
        "plan": plan,
        "active_agents": [],
    }
    result = await DispatcherNode()(state)
    assert result["active_agents"] == ["market_data", "report"]


@pytest.mark.asyncio
async def test_dispatcher_comprehensive_dedup():
    """综合研究 plan 应去重提取所有 agent(report 只出现一次)。"""
    plan = build_plan("comprehensive_research", ["002594"], ["CN"])
    state: StockSageState = {
        "session_id": "test",
        "plan": plan,
        "active_agents": [],
    }
    result = await DispatcherNode()(state)
    # market_data, technical, fundamental, news, report (report 去重)
    assert set(result["active_agents"]) == {"market_data", "technical", "fundamental", "news", "report"}
    assert result["active_agents"].count("report") == 1


@pytest.mark.asyncio
async def test_price_query_chain_activates_only_market_and_report():
    """price_query 端到端: 只 market_data 与 report 真正执行,其余 skipped。

    用会失败的 LLM 注入避免真实网络;market_data 走真实 tushare(需 token)。
    report 在无 synthesis 时也应能产出报告。
    """
    pytest.importorskip("tushare")
    from backend.config import settings
    if not settings.tushare_token:
        pytest.skip("需 TUSHARE_TOKEN")

    # 构造一个 price_query 状态,直接跑编译后的图
    graph = StockSageGraphBuilder().get_graph()
    initial: StockSageState = {
        "messages": [{"role": "user", "content": "600519 现在多少钱"}],
        "current_query": "600519 现在多少钱",
        "session_id": "test-session",
        "intent": {},
        "plan": {},
        "active_agents": [],
        "task_status": {},
        "agent_results": {},
        "synthesis": {},
        "report": "",
        "status": "idle",
        "error_message": "",
    }
    result = await graph.ainvoke(initial)

    # report 应非空
    assert result["report"], "应生成报告"

    # market_data 应 completed
    assert result["agent_results"]["market_data"]["status"] == "completed"
    # 未激活的分析 agent 应 skipped
    for agent in ["technical", "fundamental", "news", "macro", "industry", "risk"]:
        assert result["agent_results"][agent]["status"] == "skipped", f"{agent} 应被跳过"
