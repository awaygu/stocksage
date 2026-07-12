"""Pytest 配置 - 将项目根目录加入 sys.path,使 backend 包可导入。

测试默认走 MockLLM(避免真实 LLM 网络调用与代理环境耦合);
tushare 数据保持真实(需 TUSHARE_TOKEN)。
真实 LLM 集成测试用 @pytest.mark.integration 标记,默认跳过。
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest


@pytest.fixture(autouse=True)
def mock_llm_for_tests(monkeypatch):
    """默认强制走 MockLLM: patch 所有引用 get_llm_for_agent 的模块。

    .env 里的 OPENAI_API_KEY 优先级高于环境变量,故采用 patch。
    base.py 用 `from ... import get_llm_for_agent` 绑定了函数对象,
    需 patch base 模块的名字才生效。
    """
    from backend.agents import base as base_mod
    from backend.core import llm_provider
    from backend.core.llm_provider import MockLLM

    def _mock_get_llm_for_agent(agent_id):
        return MockLLM(model="mock", temperature=0.1)

    # patch 源模块
    monkeypatch.setattr(llm_provider, "get_llm_for_agent", _mock_get_llm_for_agent)
    # patch 所有通过 `from ... import get_llm_for_agent` 绑定了函数对象的节点模块
    import backend.graph.nodes.report_node as report_mod
    import backend.graph.nodes.technical_node as tech_mod
    import backend.graph.nodes.fundamental_node as fund_mod
    import backend.graph.nodes.news_node as news_mod
    import backend.graph.nodes.macro_node as macro_mod
    import backend.graph.nodes.industry_node as ind_mod
    import backend.graph.nodes.risk_node as risk_mod
    for mod in (base_mod, report_mod, tech_mod, fund_mod, news_mod, macro_mod, ind_mod, risk_mod):
        if hasattr(mod, "get_llm_for_agent"):
            monkeypatch.setattr(mod, "get_llm_for_agent", _mock_get_llm_for_agent)
    yield
