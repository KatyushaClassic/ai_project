"""Excel 数据管理模块。

职责：
1. 读取多个 Excel 文件到 pandas DataFrame。
2. 对每张表提供结构化元信息（列名、类型、示例行）。
3. 为上层模块提供统一的数据访问接口。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.api.types import (
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_string_dtype,
)


@dataclass
class TableInfo:
    """表信息对象，便于跨模块传输。"""

    table_name: str
    dataframe: pd.DataFrame


class DataManager:
    """管理上传 Excel 数据的核心类。"""

    def __init__(self) -> None:
        # key: 表名（文件名），value: DataFrame
        self._tables: dict[str, pd.DataFrame] = {}

    def add_excel_file(self, file_path: str | Path) -> tuple[str, int, int]:
        """读取并登记单个 Excel 文件。

        返回：
            (表名, 行数, 列数)
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")
        if path.suffix.lower() not in {".xlsx", ".xls"}:
            raise ValueError(f"不支持的文件类型: {path.suffix}")

        # 默认读取第一个 sheet；也可以在后续扩展为多 sheet 模式
        df = pd.read_excel(path)
        df = df.dropna(how="all")  # 清理全空行
        table_name = path.name
        self._tables[table_name] = df
        return table_name, len(df), len(df.columns)

    def has_data(self) -> bool:
        """是否存在可分析的数据。"""
        return bool(self._tables)

    def get_all_tables(self) -> list[TableInfo]:
        """获取全部表数据。"""
        return [TableInfo(name, df.copy()) for name, df in self._tables.items()]

    def get_table_names(self) -> list[str]:
        """获取所有表名。"""
        return list(self._tables.keys())

    def get_table_preview(self, table_name: str, rows: int = 20) -> pd.DataFrame:
        """获取单张表预览数据。"""
        if table_name not in self._tables:
            raise KeyError(f"表不存在: {table_name}")
        return self._tables[table_name].head(rows).copy()

    def get_schema_summary(self, sample_rows: int = 5) -> list[dict[str, Any]]:
        """返回所有表结构摘要，供 prompt 构建使用。"""
        summary: list[dict[str, Any]] = []

        for table_name, df in self._tables.items():
            columns = list(df.columns)
            dtypes = {
                col: self._infer_column_type(df[col])
                for col in columns
            }

            sample_df = df.head(sample_rows).copy()
            sample_df = sample_df.where(pd.notnull(sample_df), None)
            sample_records = sample_df.to_dict(orient="records")

            summary.append(
                {
                    "table_name": table_name,
                    "row_count": int(len(df)),
                    "column_count": int(len(columns)),
                    "columns": columns,
                    "column_types": dtypes,
                    "sample_rows": sample_records,
                }
            )

        return summary

    @staticmethod
    def _infer_column_type(series: pd.Series) -> str:
        """列类型识别：数值 / 日期 / 文本 / 其他。"""
        if is_numeric_dtype(series):
            return "数值"
        if is_datetime64_any_dtype(series):
            return "日期"
        if is_string_dtype(series):
            return "文本"
        return "其他"
