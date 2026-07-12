"""DAG 模板表 - 意图类型到带依赖任务 DAG 的纯规则映射。

Planner 的"执行计划生成"逻辑集中在此,与 LLM 解耦,便于单测。
LLM 只负责意图识别 + 股票代码提取, DAG 拓扑由本模块的模板生成,
确保拓扑合法(不幻觉 agent 名、无循环依赖)。
"""

from backend.graph.state import PlanResult, TaskItem

# 所有可用 agent 标识(用于校验)
VALID_AGENTS = frozenset({
    "market_data", "technical", "fundamental", "news",
    "macro", "industry", "risk", "report",
})


def _task(task_id: str, agent: str, depends_on: list[str] | None = None, params: dict | None = None) -> TaskItem:
    """构造 TaskItem 的便捷函数。"""
    return {
        "id": task_id,
        "agent": agent,
        "depends_on": depends_on or [],
        "params": params or {},
    }


def build_plan(
    intent_type: str,
    stock_codes: list[str],
    markets: list[str],
    timeframe: str = "近一个月",
    user_query: str = "",
) -> PlanResult:
    """根据意图类型生成带依赖的执行计划 DAG。

    所有模板都以 report 收尾;report 依赖前面所有分析 agent(隐式 join)。
    纵切阶段仅 price_query 链路有真实 agent 实现,其余意图也生成合法 DAG
    (供静态图跳过逻辑使用,未实现的 agent 节点会走 skipped)。
    """
    codes_param = {"codes": stock_codes}
    tasks: list[TaskItem] = []

    if intent_type == "price_query":
        # 价格查询: 仅市场数据 + 报告
        tasks = [
            _task("T1", "market_data", [], codes_param),
            _task("T2", "report", ["T1"]),
        ]
    elif intent_type == "technical_analysis":
        tasks = [
            _task("T1", "market_data", [], codes_param),
            _task("T2", "technical", ["T1"]),
            _task("T3", "report", ["T2"]),
        ]
    elif intent_type == "fundamental_analysis":
        tasks = [
            _task("T1", "market_data", [], codes_param),
            _task("T2", "fundamental", ["T1"]),
            _task("T3", "report", ["T2"]),
        ]
    elif intent_type == "news_analysis":
        tasks = [
            _task("T1", "market_data", [], codes_param),
            _task("T2", "news", ["T1"]),
            _task("T3", "report", ["T2"]),
        ]
    elif intent_type == "risk_assessment":
        tasks = [
            _task("T1", "market_data", [], codes_param),
            _task("T2", "technical", ["T1"]),
            _task("T3", "fundamental", ["T1"]),
            _task("T4", "risk", ["T2", "T3"]),
            _task("T5", "report", ["T4"]),
        ]
    elif intent_type == "comprehensive_research":
        # 综合研究: 市场/技术/基本面/新闻 并行扇出后汇合到 report
        tasks = [
            _task("T1", "market_data", [], codes_param),
            _task("T2", "technical", ["T1"]),
            _task("T3", "fundamental", ["T1"]),
            _task("T4", "news", ["T1"]),
            _task("T5", "report", ["T2", "T3", "T4"]),
        ]
    elif intent_type == "industry_comparison":
        tasks = [
            _task("T1", "market_data", [], codes_param),
            _task("T2", "industry", ["T1"]),
            _task("T3", "report", ["T2"]),
        ]
    elif intent_type == "macro_analysis":
        tasks = [
            _task("T1", "macro", []),
            _task("T2", "report", ["T1"]),
        ]
    else:  # chat 或未知
        tasks = [
            _task("T1", "report", []),
        ]

    return {
        "intent_type": intent_type,
        "stock_codes": stock_codes,
        "markets": markets or ["CN"],
        "timeframe": timeframe,
        "tasks": tasks,
    }


def validate_plan(plan: PlanResult) -> list[str]:
    """校验计划合法性,返回错误列表(空列表表示合法)。

    检查: agent 名合法、无循环依赖、依赖的 task 存在。
    """
    errors: list[str] = []
    task_ids = {t["id"] for t in plan["tasks"]}

    for t in plan["tasks"]:
        if t["agent"] not in VALID_AGENTS:
            errors.append(f"未知 agent: {t['agent']}")
        for dep in t["depends_on"]:
            if dep not in task_ids:
                errors.append(f"任务 {t['id']} 依赖不存在的任务 {dep}")

    # 循环依赖检测(简单 DFS)
    graph = {t["id"]: t["depends_on"] for t in plan["tasks"]}
    visiting: set[str] = set()
    visited: set[str] = set()

    def has_cycle(node: str) -> bool:
        visiting.add(node)
        for dep in graph.get(node, []):
            if dep in visiting:
                return True
            if dep not in visited and has_cycle(dep):
                return True
        visiting.discard(node)
        visited.add(node)
        return False

    for tid in graph:
        if tid not in visited and has_cycle(tid):
            errors.append("检测到循环依赖")
            break

    return errors
