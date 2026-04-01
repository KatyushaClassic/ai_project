"""Excel 数据管理模块。

职责：
1. 读取多个 Excel 文件到 pandas DataFrame。
2. 自动识别表头所在行（兼容前置说明行/空行场景）。
3. 对每张表提供结构化元信息（列名、类型、示例行）。
4. 为上层模块提供统一的数据访问接口。
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import tempfile
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
        # key: 表名（文件名），value: 识别到的表头行（1-based）
        self._header_rows: dict[str, int] = {}

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

        working_path, temp_path = self._prepare_working_excel(path)
        try:
            header_idx = self._detect_header_row(working_path)

            # 默认读取第一个 sheet；可后续扩展多 sheet
            read_engine = self._select_excel_engine(working_path)
            if not read_engine:
                raise RuntimeError(self._build_engine_error_message(working_path.suffix.lower()))
            df = pd.read_excel(working_path, header=header_idx, engine=read_engine)
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)

        df = df.dropna(how="all")  # 清理全空行
        df = df.loc[:, ~df.columns.isna()]  # 清理空列名

        # 将列名标准化为字符串，防止后续 JSON 序列化异常
        df.columns = [str(col).strip() for col in df.columns]

        table_name = path.name
        self._tables[table_name] = df
        self._header_rows[table_name] = header_idx + 1  # 转为 1-based，便于展示
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

    def get_header_row(self, table_name: str) -> int:
        """获取识别到的表头行号（1-based）。"""
        if table_name not in self._tables:
            raise KeyError(f"表不存在: {table_name}")
        return self._header_rows.get(table_name, 1)

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
            dtypes = {col: self._infer_column_type(df[col]) for col in columns}

            sample_df = df.head(sample_rows).copy()
            sample_df = sample_df.where(pd.notnull(sample_df), None)
            sample_records = sample_df.to_dict(orient="records")

            summary.append(
                {
                    "table_name": table_name,
                    "header_row": self._header_rows.get(table_name, 1),
                    "row_count": int(len(df)),
                    "column_count": int(len(columns)),
                    "columns": columns,
                    "column_types": dtypes,
                    "sample_rows": sample_records,
                }
            )

        return summary

    def _detect_header_row(self, path: Path) -> int:
        """自动识别表头行（返回 0-based 行号）。

        策略：
        1. 先读取前 15 行（header=None）。
        2. 计算每行候选分数：非空单元格数 + 字符串占比 + 唯一值比例。
        3. 取分数最高行作为表头；若全空则回退到第 1 行。
        """
        read_engine = self._select_excel_engine(path)
        if not read_engine:
            raise RuntimeError(self._build_engine_error_message(path.suffix.lower()))
        preview = pd.read_excel(path, header=None, nrows=15, engine=read_engine)
        if preview.empty:
            return 0

        best_row_idx = 0
        best_score = float("-inf")

        for row_idx in range(len(preview)):
            row = preview.iloc[row_idx]
            non_null = row.dropna()
            if non_null.empty:
                continue

            non_null_count = float(len(non_null))
            string_count = float(sum(1 for v in non_null if isinstance(v, str) and v.strip()))
            unique_ratio = float(non_null.nunique(dropna=True)) / non_null_count

            # 表头行通常“非空较多 + 文本较多 + 唯一性较高”
            score = non_null_count * 2.0 + string_count * 1.5 + unique_ratio

            if score > best_score:
                best_score = score
                best_row_idx = row_idx

        return best_row_idx

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

    @staticmethod
    def _select_excel_engine(path: Path) -> str | None:
        """根据后缀选择读取引擎，优先使用 calamine（同时支持 .xls/.xlsx）。"""
        suffix = path.suffix.lower()
        has_calamine = DataManager._module_available("python_calamine")
        has_openpyxl = DataManager._module_available("openpyxl")
        has_xlrd = DataManager._module_available("xlrd")

        # pandas + calamine 同时支持 .xls 和 .xlsx，优先使用，环境最简洁
        if has_calamine:
            return "calamine"

        if suffix == ".xlsx" and has_openpyxl:
            return "openpyxl"
        if suffix == ".xls" and has_xlrd:
            return "xlrd"
        return None

    @staticmethod
    def _module_available(module_name: str) -> bool:
        return importlib.util.find_spec(module_name) is not None

    @staticmethod
    def _build_engine_error_message(suffix: str) -> str:
        if suffix == ".xls":
            return (
                "当前环境无法读取 .xls。请优先安装：pip install python-calamine；"
                "或安装备用方案：pip install xlrd==2.0.1"
            )
        return "当前环境无法读取 .xlsx。请安装：pip install openpyxl 或 python-calamine"

    def _prepare_working_excel(self, path: Path) -> tuple[Path, Path | None]:
        """将 .xls 转换为临时 .xlsx（不改动源文件），其余格式原样返回。"""
        if path.suffix.lower() != ".xls":
            return path, None
        temp_xlsx = self._convert_xls_to_temp_xlsx(path)
        return temp_xlsx, temp_xlsx

    def _convert_xls_to_temp_xlsx(self, xls_path: Path) -> Path:
        """把 .xls 读取后写入临时 .xlsx，仅用于程序内部处理。"""
        xls_engine = self._select_xls_engine()
        if not xls_engine:
            raise RuntimeError(self._build_engine_error_message(".xls"))
        if not self._module_available("openpyxl"):
            raise RuntimeError("转换 .xls 需要 openpyxl 写入 .xlsx，请安装：pip install openpyxl")

        raw_df = pd.read_excel(xls_path, header=None, engine=xls_engine)
        temp_file = tempfile.NamedTemporaryFile(prefix="xls_convert_", suffix=".xlsx", delete=False)
        temp_path = Path(temp_file.name)
        temp_file.close()
        raw_df.to_excel(temp_path, header=False, index=False, engine="openpyxl")
        return temp_path

    @staticmethod
    def _select_xls_engine() -> str | None:
        """仅用于读取 .xls 源文件。"""
        if DataManager._module_available("python_calamine"):
            return "calamine"
        if DataManager._module_available("xlrd"):
            return "xlrd"
        return None
