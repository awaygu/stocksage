"""State 定义测试 - 验证 TypedDict 结构能被 LangGraph 接受,reducer 正确。

关键验证: StockSageState 能被 StateGraph 编译(Annotated reducer 语法正确)。
"""

from langgraph.graph import StateGraph

from backend.graph.state import (
    AgentResult,
    PlanResult,
    StockSageState,
    TaskItem,
    merge_agent_results,
)


def test_task_item_structure():
    """TaskItem 应含 id/agent/depends_on/params 四字段。"""
    task: TaskItem = {"id": "T1", "agent": "market_data", "depends_on": [], "params": {"codes": ["600519"]}}
    assert task["id"] == "T1"
    assert task["agent"] == "market_data"
    assert task["depends_on"] == []
    assert task["params"]["codes"] == ["600519"]


def test_plan_result_structure():
    """PlanResult 应能表达带依赖的 DAG。"""
    plan: PlanResult = {
        "intent_type": "comprehensive_research",
        "stock_codes": ["600519"],
        "markets": ["CN"],
        "timeframe": "近一个月",
        "tasks": [
            {"id": "T1", "agent": "market_data", "depends_on": [], "params": {}},
            {"id": "T2", "agent": "technical", "depends_on": ["T1"], "params": {}},
            {"id": "T3", "agent": "report", "depends_on": ["T2"], "params": {}},
        ],
    }
    assert len(plan["tasks"]) == 3
    assert plan["tasks"][1]["depends_on"] == ["T1"]


def test_merge_agent_results_overrides():
    """reducer 应让新结果覆盖旧结果(同 agent_id)。"""
    old: dict[str, AgentResult] = {"market_data": {"agent_id": "market_data", "status": "running"}}
    new: dict[str, AgentResult] = {"market_data": {"agent_id": "market_data", "status": "completed", "summary": "ok"}}
    merged = merge_agent_results(old, new)
    assert merged["market_data"]["status"] == "completed"
    assert merged["market_data"]["summary"] == "ok"


def test_state_graph_compiles_with_new_fields():
    """StockSageState 应能被 StateGraph 接受并编译(含 task_status reducer)。

    这是核心验证: Annotated reducer 语法错误会导致 StateGraph 初始化失败。
    """

    def dummy_node(state: StockSageState) -> dict:
        return {"agent_results": {"x": {"agent_id": "x", "status": "completed"}}}

    builder = StateGraph(StockSageState)
    builder.add_node("dummy", dummy_node)
    builder.set_entry_point("dummy")
    builder.add_edge("dummy", "__end__")
    graph = builder.compile()  # 能编译即说明 state 定义合法
    assert graph is not None


def test_task_status_reducer_merges():
    """task_status 的 dict 合并 reducer 应正确合并。"""
    # 模拟 LangGraph 调用 reducer: 旧 {T1:done} 新 {T2:running}
    reducer = StockSageState.__annotations__["task_status"].__metadata__[0] if hasattr(
        StockSageState.__annotations__.get("task_status", None), "__metadata__"
    ) else None
    # 退一步: 直接验证 lambda 行为
    from backend.graph.state import StockSageState as _S
    ann = _S.__annotations__["task_status"]
    # Annotated[dict, reducer]; reducer 是 metadata[0]
    merge = ann.__metadata__[0]
    merged = merge({"T1": "completed"}, {"T2": "running"})
    assert merged == {"T1": "completed", "T2": "running"}
