"""市场数据节点 - 入口判断是否激活,未激活则跳过。"""

from backend.agents.market_data import MarketDataAgent
from backend.graph.nodes.common import is_agent_active, skip_agent
from backend.graph.state import StockSageState


class MarketDataNode:
    """市场数据节点。"""

    def __init__(self) -> None:
        self.agent = MarketDataAgent()

    async def __call__(self, state: StockSageState) -> dict:
        """执行市场数据采集;未激活则跳过。"""
        if not await is_agent_active(state, "market_data"):
            return await skip_agent(state, "market_data", "价格查询链路不需要,跳过")
        result = await self.agent.run(state)
        return {"agent_results": result}
