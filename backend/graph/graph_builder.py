"""LangGraph 工作流构建器 - Plan-and-execute 静态图。

拓扑:
  planner -> dispatcher -> [market_data, technical, fundamental, news, macro, industry, risk]
                          -> report -> END

静态图一次建好所有候选 agent 节点;dispatcher 标记 active_agents,
各 agent 节点入口读标记判断执行或跳过(skipped)。LangGraph 的多边扇出/汇入
天然提供并行与 join 语义。
"""

from langgraph.graph import END, StateGraph

from backend.graph.nodes.dispatcher_node import DispatcherNode
from backend.graph.nodes.fundamental_node import FundamentalNode
from backend.graph.nodes.industry_node import IndustryNode
from backend.graph.nodes.macro_node import MacroNode
from backend.graph.nodes.market_data_node import MarketDataNode
from backend.graph.nodes.news_node import NewsNode
from backend.graph.nodes.report_node import ReportNode
from backend.graph.nodes.risk_node import RiskNode
from backend.graph.nodes.router_node import PlannerNode
from backend.graph.nodes.technical_node import TechnicalNode
from backend.graph.state import StockSageState

# 扇出层: 所有可被 plan 激活的分析 agent(不含 planner/dispatcher/report)
ANALYSIS_AGENTS = [
    "market_data",
    "technical",
    "fundamental",
    "news",
    "macro",
    "industry",
    "risk",
]


class StockSageGraphBuilder:
    """构建 StockSage 的静态多 Agent 工作流图。"""

    def __init__(self) -> None:
        self.builder = StateGraph(StockSageState)

    def build(self) -> StateGraph:
        """构建完整的 StateGraph。"""

        # 1. 添加所有节点
        self.builder.add_node("planner", PlannerNode())
        self.builder.add_node("dispatcher", DispatcherNode())
        self.builder.add_node("market_data", MarketDataNode())
        self.builder.add_node("technical", TechnicalNode())
        self.builder.add_node("fundamental", FundamentalNode())
        self.builder.add_node("news", NewsNode())
        self.builder.add_node("macro", MacroNode())
        self.builder.add_node("industry", IndustryNode())
        self.builder.add_node("risk", RiskNode())
        self.builder.add_node("report", ReportNode())

        # 2. 入口
        self.builder.set_entry_point("planner")

        # 3. planner -> dispatcher
        self.builder.add_edge("planner", "dispatcher")

        # 4. dispatcher 扇出到所有分析 agent(并行)
        for agent in ANALYSIS_AGENTS:
            self.builder.add_edge("dispatcher", agent)

        # 5. 所有分析 agent 汇入 report(LangGraph 等所有前驱完成才执行 report)
        for agent in ANALYSIS_AGENTS:
            self.builder.add_edge(agent, "report")

        # 6. report -> END
        self.builder.add_edge("report", END)

        return self.builder.compile()

    def get_graph(self):
        """获取编译后的图。"""
        return self.build()
