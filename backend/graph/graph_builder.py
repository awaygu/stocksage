"""LangGraph 工作流构建器 - 构建 StockSage 的多Agent工作流图。"""

from langgraph.graph import END, StateGraph

from backend.graph.nodes.fundamental_node import FundamentalNode
from backend.graph.nodes.market_data_node import MarketDataNode
from backend.graph.nodes.report_node import ReportNode
from backend.graph.nodes.router_node import RouterNode
from backend.graph.nodes.synthesis_node import SynthesisNode
from backend.graph.nodes.technical_node import TechnicalNode
from backend.graph.router import route_by_intent
from backend.graph.state import StockSageState


class StockSageGraphBuilder:
    """构建 StockSage 的多Agent工作流图。

    工作流:
    1. Router -> 解析意图
    2. 根据意图路由到不同分析Agent（可并行）
    3. 所有分析完成后 -> Synthesis -> Report
    """

    def __init__(self):
        self.builder = StateGraph(StockSageState)

    def build(self) -> StateGraph:
        """构建完整的 StateGraph。"""

        # 1. 添加节点
        self.builder.add_node("router", RouterNode())
        self.builder.add_node("market_data", MarketDataNode())
        self.builder.add_node("fundamental", FundamentalNode())
        self.builder.add_node("technical", TechnicalNode())
        self.builder.add_node("synthesis", SynthesisNode())
        self.builder.add_node("report", ReportNode())

        # 2. 设置入口点
        self.builder.set_entry_point("router")

        # 3. Router 根据意图路由
        # 从 router 出发，根据意图决定下一步
        self.builder.add_conditional_edges(
            "router",
            route_by_intent,
            {
                "market_data": "market_data",
                "fundamental": "fundamental",
                "synthesis": "synthesis",  # chat 场景直接到 synthesis
            }
        )

        # 4. MarketData 完成后可以并行到 Technical
        self.builder.add_edge("market_data", "technical")

        # 5. Technical 完成后到 synthesis
        self.builder.add_edge("technical", "synthesis")

        # 6. Fundamental 完成后到 synthesis
        self.builder.add_edge("fundamental", "synthesis")

        # 7. Synthesis 到 Report
        self.builder.add_edge("synthesis", "report")

        # 8. Report 到结束
        self.builder.add_edge("report", END)

        return self.builder.compile()

    def get_graph(self):
        """获取编译后的图。"""
        return self.build()
