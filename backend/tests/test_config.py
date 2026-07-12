"""配置层测试 - 验证 settings 能正确读取 tushare token。"""

import os

from backend.config import Settings


def test_settings_has_tushare_token_field():
    """settings 实例应包含 tushare_token 字段,默认空字符串。"""
    # 不依赖 .env 文件,直接构造
    settings = Settings(_env_file=None)
    assert hasattr(settings, "tushare_token")
    assert settings.tushare_token == ""


def test_settings_reads_tushare_token_from_env(monkeypatch):
    """通过环境变量 TUSHARE_TOKEN 注入,settings 应读取到。"""
    monkeypatch.setenv("TUSHARE_TOKEN", "test_token_abc123")
    monkeypatch.setenv("OPENAI_API_KEY", "")  # 避免读取真实 .env

    settings = Settings(_env_file=None)
    assert settings.tushare_token == "test_token_abc123"


def test_settings_preserves_existing_fields():
    """新增字段不应破坏既有配置项。"""
    settings = Settings(_env_file=None)
    assert settings.backend_port == 8000
    assert settings.llm_model == "gpt-4o"
    assert settings.redis_url.startswith("redis://")
