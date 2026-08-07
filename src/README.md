# Global Translator - 全局翻译工具

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)

**Global Translator** 是一款面向 Windows 平台的桌面翻译软件，集成屏幕取词、文档翻译和实时会议翻译三大核心功能。它采用模块化设计，支持多种翻译引擎（Google、DeepL 等），并利用 OCR 和语音识别技术，帮助您在任何应用、文档或会议中快速完成翻译。

---

## ✨ 功能特性

- 📷 **屏幕翻译** – 框选屏幕任意区域，自动 OCR 识别文本并实时翻译，支持鼠标悬停或快捷键触发。
- 📄 **文档翻译** – 支持 `.docx` 和 `.pdf` 文件，保留原格式（字体、颜色、表格等），输出翻译后的文档。
- 🎙️ **会议实时翻译** – 通过系统音频捕获和本地语音识别（Faster‑Whisper），实时生成会议字幕并翻译。
- 🔄 **多引擎支持** – 内置 Google 翻译（免费）、DeepL（需 API Key）和离线翻译（Argos Translate）接口，可灵活切换。
- ⌨️ **全局热键** – 默认 `Ctrl+Shift+X` 启动屏幕选区，`Ctrl+Shift+T` 翻译剪贴板内容，操作高效。
- 🖥️ **悬浮翻译窗** – 半透明置顶显示译文，不干扰当前工作。
- ⚙️ **个性化设置** – 可调整主题、字体大小、翻译引擎、OCR 语言等。

---

## 🖥️ 系统要求

- **操作系统**：Windows 10 / 11（64 位）
- **Python**：3.10 或更高版本
- **Tesseract OCR**：5.0 或更高版本（需单独安装，见下文）
- **可选**：NVIDIA GPU（用于加速 Whisper 语音识别）

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/global-translator.git
cd global-translator

2. 创建虚拟环境并激活
python -m venv venv
venv\Scripts\activate

3. 安装依赖
若遇到 pyaudio 编译错误，请先注释掉 requirements.txt 中的 pyaudio 行（会议翻译功能需要时可后续安装）。以下命令使用清华镜像加速：

bash
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
4. 配置 Tesseract OCR
下载安装 Tesseract 5.0+

安装时勾选 “Add Tesseract to the system PATH”

如需中文识别，请额外勾选 Chinese (Simplified) 语言包

5. 运行程序
bash
python src/main.py
🛠️ 技术栈
组件	技术/库
GUI 框架	PySide6 (Qt for Python)
OCR 引擎	Tesseract / EasyOCR
翻译 API	Google Translate (deep-translator) / DeepL
文档解析	python-docx (Word), PyMuPDF (PDF)
语音识别	Faster‑Whisper (本地)
屏幕截图	mss
全局热键	keyboard
配置管理	Pydantic + JSON
日志记录	loguru
📁 项目结构
text
global-translator/
├── src/
│   ├── main.py                # 程序入口
│   ├── translator/            # 翻译引擎抽象及实现（Google, DeepL, 离线）
│   ├── ocr/                   # 屏幕 OCR（Tesseract / EasyOCR）
│   ├── capture/               # 屏幕截图与区域选择
│   ├── gui/                   # 主窗口、悬浮窗、设置界面
│   ├── document/              # Word / PDF 文档翻译（保留格式）
│   ├── audio/                 # 实时语音识别（Faster‑Whisper）
│   └── utils/                 # 配置管理、热键绑定等
├── venv/                      # 虚拟环境（不提交）
├── requirements.txt           # 项目依赖
├── setup.py                   # 安装脚本
├── LICENSE                    # MIT 许可证
└── README.md                  # 本文件
🔧 配置与自定义
设置翻译引擎：在 GUI 中下拉选择，或在 config.json 中修改 translation.engine。

修改热键：在 config.json 的 hotkeys 字段自定义组合键。

添加语言包：如需识别更多语言，请安装相应的 Tesseract 语言包，并在 OCR 代码中指定 lang 参数（如 eng+chi_sim+fra）。

🤝 贡献指南
欢迎提交 Issue 或 Pull Request。请确保代码符合 PEP 8 规范，并为新功能添加适当测试。

📄 许可证
本项目采用 MIT License 开源许可，您可以自由使用、修改和分发。

📧 联系方式
作者：Jeremy

邮箱：jeremyshu123@outlook.com

项目主页：https://github.com/Jeremy-ch-shu/global-translator

Happy Translating! 🎉

text

---

### 📌 如何使用

1. 将更新后的 `setup.py` 覆盖项目根目录下的同名文件。
2. 新建 `README.md`，将上述内容复制进去。
3. 确保根目录下已存在 `LICENSE` 文件（MIT 文本）。
4. 替换文档中的 `yourusername`、`Your Name`、`your.email@example.com` 为实际信息。

如果您需要调整或添加其他内容，请随时告诉我！
This response is AI-generated, for reference only.



