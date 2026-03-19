# 智能阅卷系统 (Smart Marking System)

## 项目简介
基于 Python + OpenCV + YOLOv5 + LLM 的智能阅卷系统，支持客观题（填涂识别）和主观题（手写识别与大模型评分）。

本系统支持**3天全功能试用**，试用期结束后需通过激活码激活。激活过程采用**硬件绑定**与**远程服务器验证**机制，确保软件授权的安全性。

## 项目结构 (Project Structure)

```
MarkingSystem/
├── config/                 # 配置文件
│   ├── answer_config/      # 答案与题型配置
│   │   ├── answer_multiple.txt
│   │   ├── question_types.txt
│   │   └── subjective_answer.txt
│   ├── weights/            # 模型权重 (YOLOv5)
│   ├── config.json         # 系统主配置
│   ├── activation.dat      # 激活文件
│   └── trial.dat           # 试用数据 (加密)
├── core/                   # 核心业务逻辑
│   ├── data/               # 数据模型
│   │   └── student.py      # 学生信息模型
│   ├── omr/                # 客观题识别 (Optical Mark Recognition)
│   │   ├── processor.py    # 阅卷主流程
│   │   ├── detector.py     # 区域检测 (YOLO/OpenCV)
│   │   ├── recognizer.py   # 填涂识别算法
│   │   └── pipeline.py     # 识别流水线封装
│   ├── subjective/         # 主观题评分
│   │   ├── grader.py       # 评分逻辑
│   │   └── llm_api.py      # 大模型接口
│   └── llm_agent.py        # 智能体核心逻辑 (New)
├── interface/              # 界面与接口层
│   ├── dialogs/            # 对话框组件
│   │   ├── activation_dialog.py
│   │   ├── system_config_dialog.py
│   │   └── smart_agent_dialog.py # 智能助手界面
│   ├── main_window.py      # PySide6 主窗口
│   └── api.py              # Flask API 接口
├── utils/                  # 通用工具
│   ├── activation.py       # 激活验证
│   ├── config_manager.py   # 配置管理 (单例)
│   ├── path_utils.py       # 路径处理
│   └── export.py           # 结果导出 (Excel)
├── yolo/                   # YOLOv5 依赖
│   ├── models/             # 模型定义
│   └── utils/              # YOLO 工具函数
├── tests/                  # 测试代码
│   └── data/               # 测试图片数据
├── main.py                 # 程序入口
├── requirements.txt        # 项目依赖
└── README.md               # 项目文档
```

## 架构概览 (Architecture)

```ascii
+-----------+       +------------------------+       +------------------------+
|  main.py  | ----> | interface.main_window  | <---> |  utils.config_manager  |
+-----------+       | (PySide6 GUI)          |       |  (Configuration)       |
      |             +------------------------+       +------------------------+
      |                        |      ^
      v                        v      |
+------------------------+  +------------------------+      +---------------------------+
|   core.omr.processor   |  |     interface.api      |      | interface.dialogs.        |
|   (Main Logic Flow)    |  |     (Flask API)        |      | smart_agent_dialog        |
+------------------------+  +------------------------+      +---------------------------+
      |            |                                                    |
      v            v                                                    v
+-----------+  +-----------+       +----------------+         +-------------------+
| core.omr. |  | core.omr. | ----> |   core.data.   |         |  core.llm_agent   |
| detector  |  | recognizer|       |   student      |         |  (LLM Agent)      |
+-----------+  +-----------+       +----------------+         +-------------------+
      |              |
      v              v
+-----------+  +-----------+
|   yolo/   |  | core.sub. |
| (YOLOv5)  |  | llm_api   |
+-----------+  +-----------+
```

## 功能特性 (Features)

### 1. 智能阅卷 (Smart Marking)
- **客观题识别**: 使用 OpenCV 和 YOLOv5 高精度定位和识别答题卡填涂。
- **主观题评分**: 结合 OCR 和 LLM (大模型) 对手写内容进行语义评分。

### 2. 智能助手 (Smart Assistant) `New`
- **多模态交互**: 支持通过文字对话或上传试卷图片进行配置。
- **自动配置**: 智能解析用户的自然语言指令或试卷图片，自动生成客观题和主观题的答案配置。
- **流式对话**: 采用类似 ChatGPT 的流式输出体验，支持气泡式对话界面。
- **模型支持**: 兼容 OpenAI 格式接口，内置支持 zai-org/GLM-4.6V, Qwen/Qwen3-VL 等多模态大模型。

### 3. 系统管理
- **试用与激活**: 内置 3 天全功能试用，支持安全的离线激活机制。
- **配置管理**: 统一的 JSON 配置管理，支持 GUI 修改系统参数。

## 模块说明 (Modules)

### Core (核心层)
- **omr.processor**: 包含 `omr_processing` 函数，是单张答题卡处理的核心入口，协调定位、识别和计分。
- **omr.detector**: 负责答题卡关键区域（定位点、学号区、答题区）的检测与校正，集成 YOLOv5 推理。
- **omr.recognizer**: 实现 `detect_rectangle_filling` 等算法，利用 OpenCV 判断填涂情况。
- **subjective.grader**: 负责主观题区域的提取，并调用 LLM API 进行评分。
- **llm_agent**: 封装与大模型的对话逻辑，支持文本和图片输入，处理流式响应。

### Interface (接口层)
- **main_window.py**: 基于 PySide6 的图形用户界面，提供批量阅卷、参数设置、结果导出等功能。
- **dialogs/**: 包含系统配置、激活验证、智能助手等独立对话框组件。
- **api.py**: 提供 HTTP 接口，支持通过 URL 或 Base64 上传图片进行阅卷。

### Utils (工具层)
- **config_manager**: 管理全局配置，支持自动加载和保存 `config.json`。
- **activation**: 处理软件激活逻辑，验证机器码与激活码。
- **path_utils**: 统一处理文件路径，适配开发环境与打包环境。

## 环境依赖 (Requirements)

请参考 `requirements.txt` 安装依赖：
```bash
pip install -r requirements.txt
```

主要依赖：
- Python 3.8+
- PySide6 (GUI)
- OpenCV (图像处理)
- PyTorch & Ultralytics (YOLOv5 推理)
- Flask (Web API)
- OpenAI (LLM 调用)
- Pandas & OpenPyXL (Excel 导出)
- Cryptography (数据加密)

## 迁移映射表 (Migration Map)

| 原文件/路径 | 新文件/路径 | 说明 |
|---|---|---|
| `批量阅卷.py` | `interface/main_window.py` | GUI 逻辑移入 interface 包 |
| (无) | `main.py` | 新增统一入口脚本 |
| `config.json` | `config/config.json` | 配置文件归档 |
| `activation.dat` | `config/activation.dat` | 激活文件归档 |
| `answer_config/` | `config/answer_config/` | 答案配置目录移动 |
| `utils/config_manager.py` | `utils/config_manager.py` | 保持不变 (已模块化) |
| `answer_interface/det_recfg.py` | `core/omr/detector.py` | 检测逻辑重命名 |
| `answer_interface/recognize_answer.py` | `core/omr/recognizer.py` | 识别逻辑重命名 |
| `answer_interface/app.py` | `interface/api.py` | API 服务重命名 |
| `yolo/` | `yolo/` | YOLO 依赖保持独立 |
| `test_*.py` | (Deleted) | 旧测试脚本已清理 |

## 快速开始 (Quick Start)

1. **安装依赖**:
   ```bash
   pip install -r requirements.txt
   ```

2. **运行程序**:
   ```bash
   python main.py
   ```
