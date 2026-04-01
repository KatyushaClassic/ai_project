"""Prompt 构建模块。"""

from __future__ import annotations

import json
from typing import Any

from utils import config


class PromptBuilder:
    """将用户问题 + 表结构信息拼装为可控长度的 prompt。"""

    @staticmethod
    def build_prompt(
        user_question: str,
        table_summaries: list[dict[str, Any]],
        conversation_history: list[dict[str, str]] | None = None,
    ) -> str:
        """生成最终发送给 Ollama 的 prompt。"""
        history_text = PromptBuilder._format_history(conversation_history or [])

        selected_tables = table_summaries[: config.MAX_TABLES_IN_PROMPT]
        table_sections: list[str] = []

        for table in selected_tables:
            section = {
                "table_name": table["table_name"],
                "header_row": table.get("header_row", 1),
                "row_count": table["row_count"],
                "column_count": table["column_count"],
                "columns": table["columns"],
                "column_types": table["column_types"],
                "sample_rows": table["sample_rows"],
            }
            table_sections.append(json.dumps(section, ensure_ascii=False, indent=2, default=str))

        data_text = "\n\n".join(table_sections)

        prompt = f"""
你是一名资深数据分析师。请基于我提供的 Excel 表结构和样例数据直接进行分析，严禁编造不存在的数据。
如果信息不足，请明确说明还需要哪些字段或样本。

【多轮对话上下文】
{history_text}

【用户当前问题】
{user_question}

【Excel数据摘要（JSON）】
{data_text}

【输出要求】
1. 用中文回答，先给结论，再给简短依据。
2. 若涉及计算，请展示关键计算逻辑（可简述）。
3. 不要输出 SQL，不要假设数据库。
4. 如果样例数据不足以得出可靠结论，请明确标注“基于样例推断”。
""".strip()

        if len(prompt) > config.MAX_CHARS_PER_PROMPT:
            prompt = prompt[: config.MAX_CHARS_PER_PROMPT] + "\n\n[提示] 由于上下文长度限制，部分数据已截断。"

        return prompt

    @staticmethod
    def _format_history(history: list[dict[str, str]]) -> str:
        if not history:
            return "（无）"

        last_messages = history[-6:]
        lines = []
        for item in last_messages:
            role = item.get("role", "user")
            content = item.get("content", "")
            prefix = "用户" if role == "user" else "AI"
            lines.append(f"- {prefix}: {content}")
        return "\n".join(lines)
