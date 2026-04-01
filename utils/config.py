"""全局配置模块。"""

from __future__ import annotations

# Ollama API 配置
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:7b"
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
