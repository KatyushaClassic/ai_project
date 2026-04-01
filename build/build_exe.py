"""PyInstaller 打包脚本。

执行方式：
    python build/build_exe.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    main_file = project_root / "main.py"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onefile",
        "--name",
        "AIExcelAnalyzer",
        "--hidden-import",
        "pandas",
        "--hidden-import",
        "openpyxl",
        "--hidden-import",
        "python_calamine",
        "--collect-all",
        "python_calamine",
        "--hidden-import",
        "xlrd",
        "--hidden-import",
        "pandas.io.excel._xlrd",
        "--collect-all",
        "xlrd",
        "--hidden-import",
        "PySide6",
        str(main_file),
    ]

    print("开始执行打包命令：")
    print(" ".join(cmd))
    subprocess.run(cmd, cwd=project_root, check=True)
    print("打包完成，可执行文件位于 dist/AIExcelAnalyzer.exe")


if __name__ == "__main__":
    main()
