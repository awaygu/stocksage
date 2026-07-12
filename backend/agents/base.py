"""Agent 基类 - 所有 Agent 的抽象基类."""

from abc import ABC, abstractmethod
from typing import Any

from backend.core.llm_provider import get_llm_for_agent
from backend.graph.state import StockSageState


class BaseAgent(ABC):
    """所有 Agent 的抽象基类。

    每个 Agent 负责一个专业领域，通过 LangGraph State 共享数据。
    """

    def __init__(self, agent_id: str, system_prompt: str | None = None, llm: Any = None):
        self.agent_id = agent_id
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.llm = llm if llm is not None else get_llm_for_agent(agent_id)

    @abstractmethod
    def _default_system_prompt(self) -> str:
        """返回默认的系统提示词。子类必须实现。"""
        pass

    @abstractmethod
    async def run(self, state: StockSageState) -> dict[str, Any]:
        """执行 Agent 逻辑。

        Args:
            state: 当前全局状态

        Returns:
            Agent 执行结果，会被合并到 state.agent_results 中
        """
        pass

    async def call_llm(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        **kwargs: Any,
    ) -> str:
        """调用 LLM，返回文本内容。

        Args:
            messages: 消息列表，每个消息是 {"role": "system|user|assistant", "content": "..."}
            temperature: 覆盖默认温度
            **kwargs: 其他 LLM 参数

        Returns:
            LLM 返回的文本内容
        """
        if temperature is not None:
            llm = self.llm.bind(temperature=temperature)
        else:
            llm = self.llm

        response = await llm.ainvoke(messages, **kwargs)
        return str(response.content)

    def create_result(
        self,
        status: str = "completed",
        data: dict | None = None,
        summary: str = "",
        charts: list[str] | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        """创建标准的 Agent 结果字典。

        Args:
            status: 执行状态
            data: 结构化数据
            summary: 文本摘要
            charts: 图表文件名列表
            error: 错误信息

        Returns:
            符合 AgentResult 格式的字典
        """
        return {
            self.agent_id: {
                "agent_id": self.agent_id,
                "status": status,
                "data": data or {},
                "summary": summary,
                "charts": charts or [],
                "error": error,
            }
        }
