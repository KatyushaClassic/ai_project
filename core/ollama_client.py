"""Ollama API 客户端模块。"""

from __future__ import annotations

from dataclasses import dataclass

import requests

from utils import config


@dataclass
class OllamaResponse:
    """统一封装模型响应。"""

    success: bool
    content: str
    error: str = ""


class OllamaClient:
    """负责调用本地 Ollama 接口。"""

    def __init__(self, api_url: str | None = None, model: str | None = None) -> None:
        self.api_url = api_url or config.OLLAMA_API_URL
        self.model = model or config.OLLAMA_MODEL

    def generate(self, prompt: str) -> OllamaResponse:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }

        try:
            resp = requests.post(self.api_url, json=payload, timeout=config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("response", "").strip()
            if not content:
                return OllamaResponse(success=False, content="", error="模型返回为空。")
            return OllamaResponse(success=True, content=content)
        except requests.RequestException as exc:
            return OllamaResponse(success=False, content="", error=f"Ollama 请求失败: {exc}")
        except ValueError as exc:
            return OllamaResponse(success=False, content="", error=f"响应解析失败: {exc}")
