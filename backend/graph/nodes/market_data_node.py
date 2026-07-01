"""市场数据节点。"""

from backend.agents.market_data import MarketDataAgent
from backend.graph.state import StockSageState


class MarketDataNode:
    """市场数据节点。"""

    def __init__(self):
        self.agent = MarketDataAgent()

    async def __call__(self, state: StockSageState) -> dict:
        """执行市场数据采集。"""
        result = await self.agent.run(state)
        return {"agent_results": result}
