"""全局配置模块。"""

from __future__ import annotations

import os

# Ollama API 配置
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_API_URL = f"{OLLAMA_BASE_URL.rstrip('/')}/api/generate"
OLLAMA_TAGS_URL = f"{OLLAMA_BASE_URL.rstrip('/')}/api/tags"
OLLAMA_PS_URL = f"{OLLAMA_BASE_URL.rstrip('/')}/api/ps"
# 不设置默认模型：优先自动选择当前正在运行的模型。
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "").strip()
REQUEST_TIMEOUT = 120

# Prompt 构建配置
MAX_SAMPLE_ROWS_PER_TABLE = 5
MAX_TABLES_IN_PROMPT = 8
MAX_CHARS_PER_PROMPT = 12_000

# UI 配置
APP_TITLE = "AI Excel 数据分析助手"
WINDOW_WIDTH = 1100
WINDOW_HEIGHT = 760
LOADING_TEXT = "AI 正在分析，请稍候..."
