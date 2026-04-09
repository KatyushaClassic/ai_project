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
        self.ps_url = config.OLLAMA_PS_URL
        self.model = model or config.OLLAMA_MODEL

    def check_connection(self) -> OllamaResponse:
        """检查 Ollama 服务并自动选择可用模型。"""
        try:
            resp = requests.get(self.tags_url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            installed_models = self._extract_model_names(data)
            running_models = self._fetch_running_models()

            selected = self._select_model(
                installed_models=installed_models,
                running_models=running_models,
                preferred_model=self.model,
            )
            if not selected:
                available = "、".join(installed_models) if installed_models else "（无）"
                return OllamaResponse(
                    success=False,
                    content="",
                    error=(
                        "已连接 Ollama，但没有可用模型。"
                        f"当前已安装模型：{available}。"
                        "请先执行 `ollama pull <你的模型名>`，然后重试。"
                    ),
                )
            self.model = selected
            return OllamaResponse(
                success=True,
                content=f"Ollama 服务连接正常，已选择模型：{self.model}。",
            )
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

    @staticmethod
    def _extract_model_names(tags_response: dict) -> list[str]:
        """兼容 Ollama 不同版本返回字段：name / model。"""
        names: list[str] = []
        for item in tags_response.get("models", []):
            candidate = item.get("name") or item.get("model") or ""
            candidate = str(candidate).strip()
            if candidate:
                names.append(candidate)
        return names

    def _fetch_running_models(self) -> list[str]:
        """获取当前正在运行的模型列表。接口不可用时返回空列表。"""
        try:
            resp = requests.get(self.ps_url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return self._extract_model_names(data)
        except (requests.RequestException, ValueError):
            return []

    @staticmethod
    def _match_model_name(models: list[str], target: str) -> str:
        """模型匹配：精确匹配 > 忽略大小写 > 基础名匹配（冒号前）。"""
        if not target:
            return ""
        if not models:
            return ""

        target_clean = target.strip()
        target_lower = target_clean.lower()

        # 1) 精确匹配（含大小写）
        for name in models:
            if name == target_clean:
                return name

        # 2) 忽略大小写
        for name in models:
            if name.lower() == target_lower:
                return name

        # 3) 仅按基础模型名匹配（例如 qwen3）
        target_base = target_lower.split(":", maxsplit=1)[0]
        for name in models:
            base = name.lower().split(":", maxsplit=1)[0]
            if base == target_base:
                return name

        return ""

    def _select_model(
        self,
        installed_models: list[str],
        running_models: list[str],
        preferred_model: str,
    ) -> str:
        """选择模型策略：用户指定 > 运行中模型 > 已安装模型。"""
        preferred_match = self._match_model_name(installed_models, preferred_model)
        if preferred_match:
            return preferred_match

        if running_models:
            return running_models[0]
        if installed_models:
            return installed_models[0]
        return ""

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
