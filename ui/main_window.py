"""主窗口 UI 模块。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.data_manager import DataManager
from core.ollama_client import OllamaClient
from utils import config
from utils.prompt_builder import PromptBuilder


@dataclass
class ChatMessage:
    role: str
    content: str


class AnalysisWorker(QObject):
    """后台分析线程 Worker，避免阻塞 UI。"""

    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, client: OllamaClient, prompt: str) -> None:
        super().__init__()
        self.client = client
        self.prompt = prompt

    def run(self) -> None:
        result = self.client.generate(self.prompt)
        if result.success:
            self.finished.emit(result.content)
        else:
            self.failed.emit(result.error)


class MainWindow(QMainWindow):
    """应用主窗口。"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(config.APP_TITLE)
        self.resize(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)

        self.data_manager = DataManager()
        self.ollama_client = OllamaClient()
        self.chat_history: list[ChatMessage] = []

        self._worker_thread: QThread | None = None
        self._worker: AnalysisWorker | None = None

        self._init_ui()

    def _init_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)

        main_layout = QVBoxLayout(root)

        splitter = QSplitter()
        main_layout.addWidget(splitter)

        # 左侧：聊天区域
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)

        self.chat_view = QTextEdit()
        self.chat_view.setReadOnly(True)
        self.chat_view.setPlaceholderText("欢迎使用 AI Excel 数据分析助手")
        chat_layout.addWidget(QLabel("对话窗口"))
        chat_layout.addWidget(self.chat_view)

        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("请输入你的分析问题（可多行）")
        self.input_box.setFixedHeight(120)
        chat_layout.addWidget(self.input_box)

        button_layout = QHBoxLayout()
        self.send_btn = QPushButton("发送")
        self.add_file_btn = QPushButton("添加 Excel 文件")
        self.loading_label = QLabel("")
        button_layout.addWidget(self.send_btn)
        button_layout.addWidget(self.add_file_btn)
        button_layout.addWidget(self.loading_label)
        chat_layout.addLayout(button_layout)

        splitter.addWidget(chat_container)

        # 右侧：文件与数据预览（加分项）
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.addWidget(QLabel("已加载数据表"))

        self.table_list = QListWidget()
        self.preview_table = QTableWidget()

        right_layout.addWidget(self.table_list)
        right_layout.addWidget(QLabel("表数据预览（前20行）"))
        right_layout.addWidget(self.preview_table)

        splitter.addWidget(right_container)
        splitter.setSizes([760, 340])

        self.send_btn.clicked.connect(self._on_send_clicked)
        self.add_file_btn.clicked.connect(self._on_add_file_clicked)
        self.table_list.itemSelectionChanged.connect(self._on_table_selected)

    def _append_chat(self, role: str, content: str) -> None:
        """渲染聊天消息。"""
        if role == "user":
            html = f"<p><b style='color:#2563eb'>你：</b>{content}</p>"
        else:
            html = f"<p><b style='color:#16a34a'>AI：</b>{content}</p>"

        self.chat_view.append(html)
        self.chat_history.append(ChatMessage(role=role, content=content))

    def _on_add_file_clicked(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择 Excel 文件",
            "",
            "Excel Files (*.xlsx *.xls)",
        )
        if not files:
            return

        added_msgs = []
        for file_path in files:
            try:
                table_name, rows, cols = self.data_manager.add_excel_file(file_path)
                header_row = self.data_manager.get_header_row(table_name)
                added_msgs.append(f"{table_name}（表头第{header_row}行，{rows}行, {cols}列）")
            except Exception as exc:  # noqa: BLE001 - GUI 兜底提示
                QMessageBox.warning(self, "文件加载失败", f"{file_path}\n错误：{exc}")

        self._refresh_table_list()
        if added_msgs:
            self._append_chat("assistant", "已加载数据表：" + "；".join(added_msgs))

    def _refresh_table_list(self) -> None:
        self.table_list.clear()
        for name in self.data_manager.get_table_names():
            self.table_list.addItem(QListWidgetItem(name))

    def _on_table_selected(self) -> None:
        items = self.table_list.selectedItems()
        if not items:
            return

        table_name = items[0].text()
        df = self.data_manager.get_table_preview(table_name, rows=20)
        self._load_dataframe_to_table(df)

    def _load_dataframe_to_table(self, df: pd.DataFrame) -> None:
        self.preview_table.clear()
        self.preview_table.setRowCount(len(df))
        self.preview_table.setColumnCount(len(df.columns))
        self.preview_table.setHorizontalHeaderLabels([str(col) for col in df.columns])

        for row_idx in range(len(df)):
            for col_idx, col in enumerate(df.columns):
                value = "" if pd.isna(df.iloc[row_idx, col_idx]) else str(df.iloc[row_idx, col_idx])
                self.preview_table.setItem(row_idx, col_idx, QTableWidgetItem(value))

        self.preview_table.resizeColumnsToContents()

    def _on_send_clicked(self) -> None:
        question = self.input_box.toPlainText().strip()
        if not question:
            QMessageBox.information(self, "提示", "请输入问题后再发送。")
            return
        if not self.data_manager.has_data():
            QMessageBox.warning(self, "提示", "请先添加至少一个 Excel 文件。")
            return

        self.input_box.clear()
        self._append_chat("user", question)
        self.loading_label.setText(config.LOADING_TEXT)
        self.send_btn.setEnabled(False)

        summaries = self.data_manager.get_schema_summary(sample_rows=config.MAX_SAMPLE_ROWS_PER_TABLE)
        history_dicts = [{"role": m.role, "content": m.content} for m in self.chat_history]
        prompt = PromptBuilder.build_prompt(
            user_question=question,
            table_summaries=summaries,
            conversation_history=history_dicts,
        )

        self._start_worker(prompt)

    def _start_worker(self, prompt: str) -> None:
        self._worker_thread = QThread(self)
        self._worker = AnalysisWorker(self.ollama_client, prompt)
        self._worker.moveToThread(self._worker_thread)

        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_analysis_success)
        self._worker.failed.connect(self._on_analysis_failed)

        # 清理线程
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.failed.connect(self._worker_thread.quit)
        self._worker_thread.finished.connect(self._worker.deleteLater)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)

        self._worker_thread.start()

    def _on_analysis_success(self, result: str) -> None:
        self.loading_label.setText("")
        self.send_btn.setEnabled(True)
        self._append_chat("assistant", result)

    def _on_analysis_failed(self, error: str) -> None:
        self.loading_label.setText("")
        self.send_btn.setEnabled(True)
        self._append_chat("assistant", f"分析失败：{error}")
