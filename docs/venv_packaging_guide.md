# 虚拟环境打包指南（Windows）

> 目标：在**独立虚拟环境**中打包，避免系统 Python 依赖污染。

## 1) 创建并激活虚拟环境

```bat
cd /d D:\your_project_path\ai_project
python -m venv .venv
.venv\Scripts\activate
```

激活后命令行前面会出现 `(.venv)`。

## 2) 升级基础工具

```bat
python -m pip install --upgrade pip setuptools wheel
```

## 3) 安装打包与运行依赖

```bat
pip install pyinstaller pandas requests pyside6 openpyxl python-calamine xlrd==2.0.1
```

## 4) 先本地运行验证（可选但推荐）

```bat
python main.py
```

## 5) 执行打包脚本

```bat
python build\build_exe.py
```

成功后输出：

- `dist\AIExcelAnalyzer.exe`

## 6) 常见问题

### A. `.xls` 读取报错

先确认当前虚拟环境中依赖存在：

```bat
python -c "import python_calamine, openpyxl, xlrd; print('ok')"
```

### B. `ollama` 连接失败

确保本机已启动 Ollama：

```bat
ollama serve
ollama pull qwen3:14b
```

并在同一台机器上运行 `AIExcelAnalyzer.exe`。

## 7) 重新打包前清理（推荐）

```bat
rmdir /s /q build
rmdir /s /q dist
del /q *.spec
python build\build_exe.py
```

## 8) 在虚拟机打包、物理机运行（你当前场景）

这种方式可以，但必须满足以下条件：

1. **系统位数一致**：虚拟机和物理机都要是 64 位（或都 32 位）。
2. **系统大版本尽量一致**：例如都为 Windows 10/11，避免底层运行库差异。
3. **虚拟机里安装的依赖要完整**：`python-calamine/openpyxl/xlrd/pyside6` 必须都在同一个 `.venv` 中。
4. **物理机要有本地 Ollama 与模型**：`ollama serve` + `ollama pull <model>`。

建议额外做两件事：

- 打包时先在虚拟机里运行一次 `dist\\AIExcelAnalyzer.exe` 自测通过后再拷贝。
- 如果物理机仍异常，优先改为 `--onedir` 打包（比 `--onefile` 更稳，排障更容易）。

### 快速自检命令（虚拟机中执行）

```bat
python -c "import python_calamine, openpyxl, xlrd, pandas, PySide6, requests; print('deps ok')"
python -c "import platform; print(platform.platform(), platform.architecture())"
```
