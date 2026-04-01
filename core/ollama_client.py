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
        self.tags_url = config.OLLAMA_TAGS_URL
        self.model = model or config.OLLAMA_MODEL

    def check_connection(self) -> OllamaResponse:
        """检查 Ollama 服务与模型可用性。"""
        try:
            resp = requests.get(self.tags_url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            models = [item.get("name", "") for item in data.get("models", [])]
            if not any(name.startswith(self.model) for name in models):
                return OllamaResponse(
                    success=False,
                    content="",
                    error=f"已连接 Ollama，但未找到模型：{self.model}。请先执行 `ollama pull {self.model}`。",
                )
            return OllamaResponse(success=True, content="Ollama 服务连接正常。")
        except requests.RequestException as exc:
            return OllamaResponse(
                success=False,
                content="",
                error=(
                    "无法连接本地 Ollama。请确认服务已启动（`ollama serve`），"
                    f"并检查地址：{self.tags_url}。原始错误：{exc}"
                ),
            )
        except ValueError as exc:
            return OllamaResponse(success=False, content="", error=f"Ollama 响应解析失败: {exc}")

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
