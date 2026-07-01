"""LLM Provider - 封装 OpenAI 兼容 API，供所有 Agent 共享使用."""

import os
from functools import lru_cache
from typing import Any

from langchain_openai import ChatOpenAI

from backend.config import settings


class MockLLM:
    """模拟 LLM - 当没有配置 API Key 时使用。

    返回预设的模拟响应，用于测试和演示。
    """

    def __init__(self, model: str = "mock", temperature: float = 0.1):
        self.model = model
        self.temperature = temperature

    async def ainvoke(self, messages: list[dict], **kwargs: Any) -> Any:
        """模拟异步调用。"""
        # 提取最后一条用户消息
        last_msg = messages[-1] if messages else {"content": ""}
        content = last_msg.get("content", "")

        # 模拟 Router Agent 响应
        if "路由" in content or "意图" in content or "query" in content.lower():
            import re
            codes = re.findall(r'\b\d{6}\b', content)
            mock_response = (
                '{"intent_type": "comprehensive_research", '
                f'"stock_codes": {codes if codes else []}, '
                '"markets": ["CN"], '
                '"timeframe": "近一个月", '
                '"required_agents": ["market_data", "synthesis", "report"], '
                '"confidence": 0.85, '
                '"user_query": "' + content.split(":")[-1].strip() + '"}'
            )
        # 模拟技术分析
        elif "技术" in content:
            mock_response = """## 技术面分析

**趋势判断**: 近期股价处于震荡上行趋势中。MA5、MA10、MA20均线呈多头排列，短期趋势向好。

**MACD指标**: MACD在零轴上方运行，柱状体红色放大，多头动能增强。

**RSI指标**: RSI(14)约55，处于中性偏强区域，未进入超买区间，仍有上涨空间。

**支撑与压力**: 下方支撑位在MA20均线附近，上方压力位参考前期高点。

**结论**: 技术面整体偏多，短期仍有上涨动能，但需关注量能配合情况。"""
        # 模拟基本面分析
        elif "基本面" in content or "财务" in content:
            mock_response = """## 基本面分析

**盈利能力**: 公司ROE约15%，毛利率稳定在40%左右，净利润率约20%，盈利水平良好。

**估值水平**: 当前PE约25倍，PB约3.5倍，处于行业中等偏下水平，估值相对合理。

**成长性**: 近3年营收复合增长率约18%，净利润复合增长率约22%，成长性良好。

**财务健康**: 资产负债率约45%，现金流充裕，财务状况稳健。

**结论**: 基本面扎实，估值合理，适合中长期持有。"""
        # 模拟综合决策
        elif "综合" in content or "投资" in content:
            mock_response = """## 综合投资结论

**投资评级: 买入**

**核心观点:**
1. 技术面呈现多头趋势，短期仍有上涨动能
2. 基本面扎实，估值合理，具备安全边际
3. 行业景气度向好，公司竞争优势明显

**风险提示:**
1. 市场整体波动风险
2. 宏观经济政策变化可能影响行业景气度

**结论**: 综合考虑技术面和基本面因素，该股票当前处于较好的投资时机，建议适量买入并持有。"""
        # 模拟报告生成
        elif "报告" in content or "研究报告" in content:
            mock_response = """# 股票研究报告

## 一、投资摘要

该股票基本面扎实，技术面偏多，当前处于较好的投资时机，建议关注。

## 二、市场数据概览

近期股价震荡上行，成交量温和放大，市场情绪积极。

## 三、技术面分析

均线系统呈多头排列，MACD在零轴上方运行，短期趋势向好。RSI处于中性偏强区域，仍有上涨空间。

## 四、基本面分析

ROE约15%，毛利率40%，估值处于行业中等水平。近3年营收和利润复合增长率均在20%左右，成长性良好。

## 五、综合投资结论

**投资评级: 买入**

技术面和基本面均呈现积极信号，建议适量买入并持有。

## 六、风险提示

1. 市场整体波动风险
2. 宏观经济政策变化风险

---

*报告生成于 StockSage 多Agent股票研究系统*
*注: 本报告为模拟数据，仅供参考，不构成投资建议*"""
        else:
            mock_response = f"收到您的查询: {content[:50]}...\n\n(当前使用模拟模式，未配置LLM API Key)"

        # 返回一个类似 ChatOpenAI 响应的对象
        class MockResponse:
            def __init__(self, content: str):
                self.content = content
        return MockResponse(mock_response)

    def bind(self, **kwargs: Any) -> "MockLLM":
        """返回自身，支持链式调用。"""
        return self


@lru_cache()
def get_llm(model: str | None = None, temperature: float | None = None) -> ChatOpenAI | MockLLM:
    """获取 LLM 实例。

    通过环境变量配置：
    - OPENAI_BASE_URL: API 基础 URL
    - OPENAI_API_KEY: API 密钥
    - LLM_MODEL: 模型名称 (默认 gpt-4o)
    - LLM_TEMPERATURE: 温度参数 (默认 0.1)

    如果没有配置 API Key，返回 MockLLM（模拟模式）。

    Args:
        model: 覆盖默认模型名称
        temperature: 覆盖默认温度

    Returns:
        ChatOpenAI 或 MockLLM 实例
    """
    api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY", "")

    # 如果没有 API Key，使用模拟 LLM
    if not api_key or api_key == "your-api-key-here":
        print("[WARN] 未配置 OPENAI_API_KEY，使用 MockLLM 模拟模式")
        return MockLLM(
            model=model or settings.llm_model,
            temperature=temperature if temperature is not None else settings.llm_temperature,
        )

    return ChatOpenAI(
        model=model or settings.llm_model,
        temperature=temperature if temperature is not None else settings.llm_temperature,
        base_url=settings.openai_base_url,
        api_key=api_key,
        max_retries=3,
    )


@lru_cache()
def get_llm_for_agent(agent_id: str) -> ChatOpenAI | MockLLM:
    """为特定 Agent 获取 LLM 实例，允许不同 Agent 使用不同温度。

    Args:
        agent_id: Agent 标识符

    Returns:
        ChatOpenAI 或 MockLLM 实例
    """
    # Router Agent 用较低温度以获得更稳定的意图解析
    if agent_id == "router":
        temperature = 0.05
    # Report Agent 用略高温度以获得更丰富的表达
    elif agent_id == "report":
        temperature = 0.3
    else:
        temperature = settings.llm_temperature

    return get_llm(temperature=temperature)
