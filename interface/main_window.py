import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QPushButton, QFileDialog,
                               QTableWidget, QTableWidgetItem, QHeaderView, 
                               QProgressBar, QSplitter, QFrame, QGridLayout,
                               QGroupBox, QDialog, QTabWidget, QLineEdit, QFormLayout,
                               QTextEdit, QMessageBox, QComboBox, QSpinBox, 
                               QDoubleSpinBox, QListWidget, QCheckBox, QStackedWidget)
from PySide6.QtCore import Qt, Signal, QSize, QEvent
from PySide6.QtGui import QPixmap, QFont, QIcon, QColor
import pandas as pd
import os
import traceback
import re
import time
from typing import Dict, List
from core.data.student import StudentInfo
from core.omr.processor import omr_processing
# 添加激活模块导入
from utils.activation import ActivationManager
from interface.dialogs.activation_dialog import ActivationDialog
from interface.dialogs.smart_agent_dialog import SmartAgentDialog
# 添加配置管理器导入
from utils.config_manager import config_manager

# 设置工作目录为可执行文件所在目录（用于打包后解决路径问题）
if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))

# 添加配置对话框类
class AnswerConfigDialog(QDialog):
    """答案配置对话框"""
    def __init__(self, parent, questions_dict):
        super().__init__(parent)
        self.questions_dict = questions_dict.copy()
        self.init_ui()
        self.load_questions()
    
    def init_ui(self):
        self.setWindowTitle("配置答案")
        self.setModal(True)
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # 题目选择
        question_layout = QHBoxLayout()
        question_layout.addWidget(QLabel("选择题目:"))
        self.question_combo = QComboBox()
        self.question_combo.currentTextChanged.connect(self.on_question_changed)
        question_layout.addWidget(self.question_combo)
        question_layout.addStretch()
        layout.addLayout(question_layout)
        
        # 题目信息显示
        info_layout = QHBoxLayout()
        self.question_info_label = QLabel()
        info_layout.addWidget(self.question_info_label)
        layout.addLayout(info_layout)
        
        # 答案输入区域
        answer_group = QGroupBox("答案配置")
        answer_layout = QVBoxLayout(answer_group)
        
        # 单选题答案
        single_layout = QHBoxLayout()
        single_layout.addWidget(QLabel("单选答案:"))
        self.single_answer_combo = QComboBox()
        self.single_answer_combo.addItems(['A', 'B', 'C', 'D', 'E', 'F'])
        single_layout.addWidget(self.single_answer_combo)
        single_layout.addStretch()
        answer_layout.addLayout(single_layout)
        
        # 多选题答案
        multi_layout = QHBoxLayout()
        multi_layout.addWidget(QLabel("多选答案:"))
        self.multi_answer_text = QLineEdit()
        self.multi_answer_text.setPlaceholderText("输入多个答案，用逗号分隔，如：A,B,C")
        multi_layout.addWidget(self.multi_answer_text)
        answer_layout.addLayout(multi_layout)
        
        # 保存当前题目答案按钮
        save_current_btn = QPushButton("保存当前题目答案")
        save_current_btn.clicked.connect(self.save_current_answer)
        answer_layout.addWidget(save_current_btn)
        
        layout.addWidget(answer_group)
        
        # 已配置答案列表
        list_group = QGroupBox("已配置答案")
        list_layout = QVBoxLayout(list_group)
        
        self.answer_list = QListWidget()
        list_layout.addWidget(self.answer_list)
        
        layout.addWidget(list_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def load_questions(self):
        """加载题目到下拉框"""
        self.question_combo.clear()
        for q_num in sorted(self.questions_dict.keys()):
            self.question_combo.addItem(f"第{q_num}题")
        
        if self.questions_dict:
            self.on_question_changed()
    
    def on_question_changed(self):
        """题目选择改变时的处理"""
        current_text = self.question_combo.currentText()
        if not current_text:
            return
        
        # 提取题号
        q_num = int(current_text.replace("第", "").replace("题", ""))
        q_data = self.questions_dict[q_num]
        
        # 更新题目信息
        self.question_info_label.setText(f"题目类型: {q_data['type']}，分值: {q_data['score']}分")
        
        # 根据题目类型显示相应的输入控件
        if q_data['type'] == '单选题':
            self.single_answer_combo.setVisible(True)
            self.multi_answer_text.setVisible(False)
            # 设置当前答案
            if q_data['answer']:
                index = self.single_answer_combo.findText(q_data['answer'])
                if index >= 0:
                    self.single_answer_combo.setCurrentIndex(index)
        else:  # 多选题
            self.single_answer_combo.setVisible(False)
            self.multi_answer_text.setVisible(True)
            # 设置当前答案
            if q_data['answer']:
                if isinstance(q_data['answer'], list):
                    self.multi_answer_text.setText(','.join(q_data['answer']))
                else:
                    self.multi_answer_text.setText(str(q_data['answer']))
        
        # 更新已配置答案列表
        self.update_answer_list()
    
    def save_current_answer(self):
        """保存当前题目的答案"""
        current_text = self.question_combo.currentText()
        if not current_text:
            return
        
        q_num = int(current_text.replace("第", "").replace("题", ""))
        q_data = self.questions_dict[q_num]
        
        if q_data['type'] == '单选题':
            answer = self.single_answer_combo.currentText()
        else:  # 多选题
            answer_text = self.multi_answer_text.text().strip()
            if not answer_text:
                QMessageBox.warning(self, "输入错误", "请输入多选答案")
                return
            answer = [a.strip().upper() for a in answer_text.split(',') if a.strip()]
        
        # 保存答案
        self.questions_dict[q_num]['answer'] = answer
        
        # 更新答案列表
        self.update_answer_list()
        
        # 自动跳转到下一题（无弹窗）
        self.jump_to_next_question()
    
    def jump_to_next_question(self):
        """跳转到下一题"""
        current_index = self.question_combo.currentIndex()
        total_count = self.question_combo.count()
        
        # 如果不是最后一题，跳转到下一题
        if current_index < total_count - 1:
            self.question_combo.setCurrentIndex(current_index + 1)
        else:
            # 如果是最后一题，提示用户已完成所有题目配置
            QMessageBox.information(self, "配置完成", "已完成所有题目的答案配置！")
    
    def update_answer_list(self):
        """更新已配置答案列表"""
        self.answer_list.clear()
        
        for q_num in sorted(self.questions_dict.keys()):
            q_data = self.questions_dict[q_num]
            answer = q_data['answer']
            
            if answer:
                if isinstance(answer, list):
                    answer_str = ','.join(answer)
                else:
                    answer_str = str(answer)
                
                item_text = f"第{q_num}题 ({q_data['type']}, {q_data['score']}分): {answer_str}"
            else:
                item_text = f"第{q_num}题 ({q_data['type']}, {q_data['score']}分): 未配置"
            
            self.answer_list.addItem(item_text)
    
    def get_answers(self):
        """获取配置的答案"""
        return self.questions_dict


class SystemConfigDialog(QDialog):
    config_saved = Signal(dict)
    
    def __init__(self, parent=None, current_config=None):
        super().__init__(parent)
        self.setWindowTitle("系统配置")
        self.setMinimumSize(600, 400)
        self._dblclick_edit_targets = {}
        
        # 初始化配置管理器
        from utils.config_manager import config_manager
        self.config_manager = config_manager
        
        self.current_config = current_config or {
            "objective_answer": {},
            "subjective_answer": {},
            "question_types": {},
            "api_key": ""
        }
        
        # 初始化配置数据
        self.objective_questions = {}  # 客观题配置
        self.subjective_questions = {}  # 主观题配置
        
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        # 创建选项卡
        tab_widget = QTabWidget()

        # 客观题答案配置选项卡
        objective_tab = QWidget()
        objective_layout = QVBoxLayout(objective_tab)

        # 题目配置区域
        config_group = QGroupBox("题目配置")
        config_layout = QGridLayout(config_group)
        
        # 起始题号
        config_layout.addWidget(QLabel("起始题号:"), 0, 0)
        self.start_question_spin = QSpinBox()
        self.start_question_spin.setMinimum(1)
        self.start_question_spin.setMaximum(999)
        self.start_question_spin.setValue(1)
        config_layout.addWidget(self.start_question_spin, 0, 1)
        
        # 结束题号
        config_layout.addWidget(QLabel("结束题号:"), 0, 2)
        self.end_question_spin = QSpinBox()
        self.end_question_spin.setMinimum(1)
        self.end_question_spin.setMaximum(999)
        self.end_question_spin.setValue(20)
        config_layout.addWidget(self.end_question_spin, 0, 3)
        
        # 题目类型
        config_layout.addWidget(QLabel("题目类型:"), 1, 0)
        self.question_type_combo = QComboBox()
        self.question_type_combo.addItems(["单选题", "多选题"])
        config_layout.addWidget(self.question_type_combo, 1, 1)
        
        # 每题分数
        config_layout.addWidget(QLabel("每题分数:"), 1, 2)
        self.score_spin = QDoubleSpinBox()
        self.score_spin.setMinimum(0.1)
        self.score_spin.setMaximum(100.0)
        self.score_spin.setValue(1.0)
        self.score_spin.setSingleStep(0.1)
        config_layout.addWidget(self.score_spin, 1, 3)
        
        # 选项个数
        config_layout.addWidget(QLabel("选项个数:"), 2, 0)
        self.options_spin = QSpinBox()
        self.options_spin.setMinimum(2)
        self.options_spin.setMaximum(10)
        self.options_spin.setValue(4)
        self.options_spin.setToolTip("设置选择题的选项个数\n4个选项: A,B,C,D\n5个选项: A,B,C,D,E\n6个选项: A,B,C,D,E,F")
        config_layout.addWidget(self.options_spin, 2, 1)
        
        # 添加题目按钮
        add_questions_btn = QPushButton("添加题目")
        add_questions_btn.clicked.connect(self.add_questions)
        config_layout.addWidget(add_questions_btn, 3, 0, 1, 2)
        
        # 配置答案按钮
        config_answers_btn = QPushButton("配置答案")
        config_answers_btn.clicked.connect(self.config_answers)
        config_layout.addWidget(config_answers_btn, 3, 2, 1, 2)
        
        objective_layout.addWidget(config_group)

        # 已配置题目列表
        list_group = QGroupBox("已配置题目")
        list_layout = QVBoxLayout(list_group)
        
        self.questions_table = QTableWidget()
        self.questions_table.setColumnCount(5)
        self.questions_table.setHorizontalHeaderLabels(["题号", "类型", "分数", "选项数", "答案"])
        self.questions_table.horizontalHeader().setStretchLastSection(True)
        list_layout.addWidget(self.questions_table)
        # 连接表格内容修改信号
        self.questions_table.itemChanged.connect(self.on_objective_table_item_changed)
        
        # 删除选中题目按钮
        delete_btn = QPushButton("删除选中题目")
        delete_btn.clicked.connect(self.delete_selected_questions)
        list_layout.addWidget(delete_btn)
        
        objective_layout.addWidget(list_group)

        # 导入/导出按钮
        import_export_layout = QHBoxLayout()
        import_btn = QPushButton("从文件导入")
        import_btn.clicked.connect(self.import_from_file)
        export_btn = QPushButton("导出到文件")
        export_btn.clicked.connect(self.export_to_file)
        
        import_export_layout.addWidget(import_btn)
        import_export_layout.addWidget(export_btn)
        objective_layout.addLayout(import_export_layout)

        # 主观题答案配置选项卡
        subjective_tab = QWidget()
        subjective_layout = QVBoxLayout(subjective_tab)

        # 主观题配置区域
        subj_config_group = QGroupBox("主观题配置")
        subj_config_layout = QVBoxLayout(subj_config_group)
        
        # 题目信息输入
        info_layout = QGridLayout()
        info_layout.addWidget(QLabel("题目编号:"), 0, 0)
        self.subj_question_num_spin = QSpinBox()
        self.subj_question_num_spin.setMinimum(1)
        self.subj_question_num_spin.setMaximum(999)
        self.subj_question_num_spin.setValue(17)
        info_layout.addWidget(self.subj_question_num_spin, 0, 1)
        
        info_layout.addWidget(QLabel("总分:"), 0, 2)
        self.subj_total_score_spin = QDoubleSpinBox()
        self.subj_total_score_spin.setMinimum(0.1)
        self.subj_total_score_spin.setMaximum(100.0)
        self.subj_total_score_spin.setValue(12.0)
        self.subj_total_score_spin.setSingleStep(0.1)
        info_layout.addWidget(self.subj_total_score_spin, 0, 3)
        
        subj_config_layout.addLayout(info_layout)
        
        # 参考答案输入区域
        subj_config_layout.addWidget(QLabel("参考答案:"))
        self.subjective_answer_text = QTextEdit()
        self.subjective_answer_text.setPlaceholderText("请输入主观题参考答案，例如：\n（1）叶绿体（+4）    光合作用（+2）\n（2）氧气（+3）    二氧化碳（+3）")
        self.subjective_answer_text.setMaximumHeight(150)
        subj_config_layout.addWidget(self.subjective_answer_text)
        
        # 用户提示词配置区域
        subj_config_layout.addWidget(QLabel("用户提示词 (可选):"))
        self.user_prompt_text = QTextEdit()
        self.user_prompt_text.setPlaceholderText("请输入自定义的阅卷提示词，用于补充特殊的评分要求，例如：\n- 注重答案的逻辑性和完整性\n- 对于关键词给予更高权重\n- 允许同义词替换\n- 特殊评分标准说明")
        self.user_prompt_text.setMaximumHeight(120)
        subj_config_layout.addWidget(self.user_prompt_text)
        
        # 添加主观题按钮
        add_subj_btn = QPushButton("添加主观题")
        add_subj_btn.clicked.connect(self.add_subjective_question)
        subj_config_layout.addWidget(add_subj_btn)
        
        subjective_layout.addWidget(subj_config_group)

        # 已配置主观题列表
        subj_list_group = QGroupBox("已配置主观题")
        subj_list_layout = QVBoxLayout(subj_list_group)
        
        self.subjective_table = QTableWidget()
        self.subjective_table.setColumnCount(4)
        self.subjective_table.setHorizontalHeaderLabels(["题号", "总分", "参考答案", "用户提示词"])
        self.subjective_table.horizontalHeader().setStretchLastSection(True)
        subj_list_layout.addWidget(self.subjective_table)
        
        # 删除选中主观题按钮
        delete_subj_btn = QPushButton("删除选中题目")
        delete_subj_btn.clicked.connect(self.delete_selected_subjective)
        subj_list_layout.addWidget(delete_subj_btn)
        
        subjective_layout.addWidget(subj_list_group)

        # 导入/导出按钮
        subj_import_export_layout = QHBoxLayout()
        subj_import_btn = QPushButton("从文件导入")
        subj_import_btn.clicked.connect(self.import_subjective_from_file)
        subj_export_btn = QPushButton("导出到文件")
        subj_export_btn.clicked.connect(self.export_subjective_to_file)
        
        subj_import_export_layout.addWidget(subj_import_btn)
        subj_import_export_layout.addWidget(subj_export_btn)
        subjective_layout.addLayout(subj_import_export_layout)

        # API配置选项卡
        api_tab = QWidget()
        api_layout = QFormLayout(api_tab)

        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("输入SiliconFlow API密钥 (从 https://cloud.siliconflow.cn/account/ak 获取) 或其它厂商密钥")
        if self.current_config.get("api_key"):
            # 显示部分隐藏的API密钥
            api_key = self.current_config["api_key"]
            if len(api_key) > 12:  # 确保API密钥长度足够
                masked_api_key = api_key[:6] + "***" + api_key[-6:]
                self.api_key_input.setText(masked_api_key)
                # 存储原始API密钥
                self.api_key_input.setProperty("original_api_key", api_key)
            else:
                self.api_key_input.setText(api_key)

        api_layout.addRow("API密钥:", self.api_key_input)

        # 添加API基础URL配置
        self.api_base_url_input = QLineEdit()
        self.api_base_url_input.setPlaceholderText("API基础URL")
        self.api_base_url_input.setText(self.current_config.get("api_base_url", "https://api.siliconflow.cn/v1"))
        api_layout.addRow("API地址:", self.api_base_url_input)

        # 添加模型选择
        self.model_combo = QComboBox()
        # 从config.json读取可用模型列表
        available_models = self.current_config.get("available_models", [
            "Qwen/Qwen3-VL-30B-A3B-Instruct",
            "Qwen/Qwen3-VL-235B-A22B-Instruct",
            "Qwen/Qwen2.5-VL-72B-Instruct",
            "Qwen/Qwen2.5-VL-32B-Instruct",
            "stepfun-ai/step3",
            "deepseek-ai/deepseek-vl2",
            "zai-org/GLM-4.5V"
        ])
        self.model_combo.addItems(available_models)
        
        # 设置当前选中的模型
        current_model = self.current_config.get("model_name", "Qwen/Qwen3-VL-30B-A3B-Instruct")
        if current_model in available_models:
            self.model_combo.setCurrentText(current_model)
        
        api_layout.addRow("模型选择:", self.model_combo)

        api_test_layout = QHBoxLayout()
        self.test_api_button = QPushButton("测试连接")
        self.test_api_button.clicked.connect(self.test_api_connection)
        api_test_layout.addWidget(self.test_api_button)
        api_test_layout.addStretch()
        api_layout.addRow("", api_test_layout)

        self._setup_api_edit_fields()

        # 识别配置选项卡
        recognition_tab = QWidget()
        recognition_layout = QFormLayout(recognition_tab)
        self.recognition_mode_combo = QComboBox()
        self.recognition_mode_combo.addItems(["A模式（自然顺序）", "B模式（列优先）"])
        # 根据当前配置管理器的模式设置初值
        try:
            current_mode = self.config_manager.get_recognition_mode()
        except Exception:
            current_mode = "A"
        self.recognition_mode_combo.setCurrentIndex(1 if current_mode == "B" else 0)
        recognition_layout.addRow("识别模式:", self.recognition_mode_combo)

        # 题列布局（row/column）
        self.recognition_layout_combo = QComboBox()
        self.recognition_layout_combo.addItems(["一行一题（row）", "一列一题（column）"])
        try:
            current_layout = self.config_manager.get_recognition_layout()
        except Exception:
            current_layout = "row"
        self.recognition_layout_combo.setCurrentIndex(1 if current_layout == "column" else 0)
        recognition_layout.addRow("题列布局:", self.recognition_layout_combo)

        # 题组数量（每张图片包含的题数）
        from utils.config_manager import config_manager as _cm_for_group
        self.group_size_spin = QSpinBox()
        self.group_size_spin.setMinimum(1)
        self.group_size_spin.setMaximum(50)
        try:
            _group_size = _cm_for_group.get_recognition_group_size()
        except Exception:
            _group_size = 5
        self.group_size_spin.setValue(_group_size)
        self.group_size_spin.setToolTip("每张图片包含的题目数量（题组大小），最小为1")
        recognition_layout.addRow("题组数量（每图题数）:", self.group_size_spin)

        # 检测置信度阈值
        from utils.config_manager import config_manager as _cm_for_conf
        self.conf_thres_spin = QDoubleSpinBox()
        self.conf_thres_spin.setRange(0.01, 0.99)
        self.conf_thres_spin.setSingleStep(0.01)
        try:
            _conf_thres = _cm_for_conf.get_recognition_conf_thres()
        except Exception:
            _conf_thres = 0.75
        # 某些平台需要设置小数位以显示两位
        if hasattr(self.conf_thres_spin, "setDecimals"):
            self.conf_thres_spin.setDecimals(2)
        self.conf_thres_spin.setValue(float(_conf_thres))
        self.conf_thres_spin.setToolTip("YOLO检测过滤的置信度阈值，范围 0.01-0.99")
        recognition_layout.addRow("检测置信度阈值:", self.conf_thres_spin)

        self.objective_scoring_combo = QComboBox()
        self.objective_scoring_combo.addItems(["标准评分（多选全对得分）", "不定向评分（正确-错误/正确数）"])
        try:
            current_rule = self.config_manager.get_objective_scoring_rule()
        except Exception:
            current_rule = "standard"
        self.objective_scoring_combo.setCurrentIndex(1 if current_rule == "partial_penalty" else 0)
        recognition_layout.addRow("客观题评分规则:", self.objective_scoring_combo)

        # 添加选项卡
        tab_widget.addTab(objective_tab, "客观题答案")
        tab_widget.addTab(subjective_tab, "主观题答案")
        tab_widget.addTab(recognition_tab, "识别配置")
        tab_widget.addTab(api_tab, "API配置")

        layout.addWidget(tab_widget)

        # 按钮区域
        button_layout = QHBoxLayout()
        save_button = QPushButton("保存配置")
        save_button.clicked.connect(self.save_config)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        # 加载现有配置
        self.load_current_config()

    def _parse_objective_answer_file(self, file_path: str) -> dict:
        from core.omr.question_parser import parse_multiple_choice_answers
        answers, scores, options = parse_multiple_choice_answers(file_path)
        answer_dict = {}
        for q_num, answer in answers.items():
            answer_dict[q_num] = {
                'answer': answer,
                'score': scores.get(q_num, 1.0),
                'options': options.get(q_num, 4)
            }
        return answer_dict
    
    def add_questions(self):
        """添加题目到配置"""
        start_num = self.start_question_spin.value()
        end_num = self.end_question_spin.value()
        
        if start_num > end_num:
            QMessageBox.warning(self, "输入错误", "起始题号不能大于结束题号")
            return
        
        question_type = self.question_type_combo.currentText()
        score = self.score_spin.value()
        options_count = self.options_spin.value()  # 获取选项个数
        
        # 检查是否有重复题号
        existing_questions = []
        new_questions = []
        
        for q_num in range(start_num, end_num + 1):
            if q_num in self.objective_questions:
                existing_questions.append(q_num)
            else:
                new_questions.append(q_num)
        
        # 如果有重复题号，询问用户是否覆盖
        if existing_questions:
            reply = QMessageBox.question(
                self, 
                "题号重复", 
                f"题号 {existing_questions} 已存在，是否覆盖？\n点击 Yes 覆盖，点击 No 只添加新题号",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Cancel:
                return
            elif reply == QMessageBox.No:
                # 只添加新题号
                questions_to_add = new_questions
            else:
                # 覆盖所有题号
                questions_to_add = list(range(start_num, end_num + 1))
        else:
            # 没有重复，添加所有题号
            questions_to_add = list(range(start_num, end_num + 1))
        
        if not questions_to_add:
            QMessageBox.information(self, "提示", "没有新题目需要添加")
            return
        
        # 添加题目到配置
        # 确保分数保留两位小数精度
        score = round(float(score), 2)
        
        for q_num in questions_to_add:
            self.objective_questions[q_num] = {
                'type': question_type,
                'score': score,
                'options': options_count,  # 添加选项个数
                'answer': ''  # 答案稍后配置
            }
        
        # 更新表格显示
        self.update_questions_table()
        
        if existing_questions and len(questions_to_add) == len(range(start_num, end_num + 1)):
            QMessageBox.information(self, "添加成功", f"已覆盖题目 {start_num}-{end_num}（{question_type}，每题{score:.2f}分）")
        else:
            added_ranges = self.format_question_ranges(questions_to_add)
            QMessageBox.information(self, "添加成功", f"已添加题目 {added_ranges}（{question_type}，每题{score:.2f}分）")
    
    def format_question_ranges(self, question_list):
        """格式化题号列表为范围字符串"""
        if not question_list:
            return ""
        
        question_list = sorted(question_list)
        ranges = []
        start = question_list[0]
        end = start
        
        for i in range(1, len(question_list)):
            if question_list[i] == end + 1:
                end = question_list[i]
            else:
                if start == end:
                    ranges.append(str(start))
                else:
                    ranges.append(f"{start}-{end}")
                start = question_list[i]
                end = start
        
        # 添加最后一个范围
        if start == end:
            ranges.append(str(start))
        else:
            ranges.append(f"{start}-{end}")
        
        return ", ".join(ranges)
    
    def config_answers(self):
        """配置答案对话框"""
        if not self.objective_questions:
            QMessageBox.warning(self, "提示", "请先添加题目")
            return
        
        # 创建答案配置对话框
        dialog = AnswerConfigDialog(self, self.objective_questions)
        if dialog.exec() == QDialog.Accepted:
            self.objective_questions = dialog.get_answers()
            self.update_questions_table()
    
    def update_questions_table(self):
        """更新题目表格显示"""
        self.questions_table.blockSignals(True)
        self.questions_table.setRowCount(len(self.objective_questions))
        
        for row, (q_num, q_data) in enumerate(sorted(self.objective_questions.items())):
            # 题号设置为不可编辑
            q_num_item = QTableWidgetItem(str(q_num))
            q_num_item.setFlags(q_num_item.flags() & ~Qt.ItemIsEditable)
            self.questions_table.setItem(row, 0, q_num_item)
            
            self.questions_table.setItem(row, 1, QTableWidgetItem(q_data['type']))
            
            # 格式化分数显示
            score = q_data['score']
            if isinstance(score, float):
                # 尝试转为整数，如果是整数则不显示小数位，否则显示一位或两位小数
                if score.is_integer():
                    score_str = str(int(score))
                else:
                    # 去除多余的0
                    score_str = f"{score:.2f}".rstrip('0').rstrip('.')
            else:
                score_str = str(score)
                
            self.questions_table.setItem(row, 2, QTableWidgetItem(score_str))
            # 添加选项数显示
            options_count = q_data.get('options', 4)  # 默认4个选项
            self.questions_table.setItem(row, 3, QTableWidgetItem(str(options_count)))
            # 修复答案显示，确保传入字符串
            answer = q_data.get('answer', '')
            if isinstance(answer, list):
                answer_text = ','.join(answer) if answer else "未配置"
            else:
                answer_text = str(answer) if answer else "未配置"
            self.questions_table.setItem(row, 4, QTableWidgetItem(answer_text))
            
        self.questions_table.blockSignals(False)
    
    def on_objective_table_item_changed(self, item):
        """处理表格内容修改"""
        row = item.row()
        col = item.column()
        
        # 获取题号（第一列）
        try:
            q_num_item = self.questions_table.item(row, 0)
            if not q_num_item:
                return
            q_num = int(q_num_item.text())
        except ValueError:
            return

        if q_num not in self.objective_questions:
            return
            
        new_value = item.text().strip()
        q_data = self.objective_questions[q_num]
        
        # 根据列更新数据
        if col == 1: # 类型
            if new_value in ['单选题', '多选题']:
                q_data['type'] = new_value
        elif col == 2: # 分数
            try:
                q_data['score'] = float(new_value)
            except ValueError:
                pass # 保持原值
        elif col == 3: # 选项数
            try:
                q_data['options'] = int(new_value)
            except ValueError:
                pass
        elif col == 4: # 答案
            # 处理答案格式
            if ',' in new_value or '，' in new_value:
                parts = new_value.replace('，', ',').split(',')
                answer_list = [p.strip().upper() for p in parts if p.strip()]
                q_data['answer'] = answer_list
            else:
                q_data['answer'] = new_value.upper()

    def delete_selected_questions(self):
        """删除选中的题目"""
        selected_rows = set()
        for item in self.questions_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请选择要删除的题目")
            return
        
        # 获取要删除的题号
        question_nums_to_delete = []
        for row in selected_rows:
            q_num_item = self.questions_table.item(row, 0)
            if q_num_item:
                question_nums_to_delete.append(int(q_num_item.text()))
        
        # 删除题目
        for q_num in question_nums_to_delete:
            if q_num in self.objective_questions:
                del self.objective_questions[q_num]
        
        # 更新表格
        self.update_questions_table()
        
        QMessageBox.information(self, "删除成功", f"已删除 {len(question_nums_to_delete)} 道题目")
    
    def import_from_file(self):
        """从文件导入客观题配置"""
        path, _ = QFileDialog.getOpenFileName(
            self, '选择客观题答案文件',
            '', '文本文件 (*.txt)'
        )
        if not path:
            return
        
        try:
            # 使用主窗口的解析方法
            answer_dict = self._parse_objective_answer_file(path)
            
            # 转换为新的格式
            for q_num, q_data in answer_dict.items():
                self.objective_questions[q_num] = {
                    'type': '单选题' if isinstance(q_data['answer'], str) else '多选题',
                    'score': q_data['score'],
                    'answer': q_data['answer'],
                    'options': q_data.get('options', 4)  # 添加选项个数支持
                }
            
            self.update_questions_table()
            QMessageBox.information(self, "导入成功", f"已导入 {len(answer_dict)} 道题目")
            
        except Exception as e:
            QMessageBox.critical(self, "导入错误", f"文件导入失败：{str(e)}")
    
    def export_to_file(self):
        """导出客观题配置到文件"""
        if not self.objective_questions:
            QMessageBox.warning(self, "提示", "没有可导出的题目")
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self, '保存客观题答案文件',
            'objective_answers.txt', '文本文件 (*.txt)'
        )
        if not path:
            return
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write("# 客观题答案配置文件\n")
                f.write("# 格式：题号:答案:分值:选项个数\n\n")
                
                for q_num in sorted(self.objective_questions.keys()):
                    q_data = self.objective_questions[q_num]
                    answer = q_data['answer']
                    score = q_data['score']
                    options = q_data.get('options', 4)  # 获取选项个数，默认为4
                    
                    if isinstance(answer, list):
                        answer_str = ','.join(answer)
                    else:
                        answer_str = str(answer)
                    
                    # 格式化分数，如果是浮点数且有小数位，保留2位，否则作为字符串直接写入（兼容旧数据）
                    if isinstance(score, float):
                         # 去除多余的0和可能的小数点
                         score_str = f"{score:.2f}".rstrip('0').rstrip('.')
                    else:
                         score_str = str(score)

                    f.write(f"{q_num}:{answer_str}:{score_str}:{options}\n")
            
            QMessageBox.information(self, "导出成功", f"已导出到 {path}")
            
        except Exception as e:
            QMessageBox.critical(self, "导出错误", f"文件导出失败：{str(e)}")
    
    def add_subjective_question(self):
        """添加主观题"""
        q_num = self.subj_question_num_spin.value()
        total_score = self.subj_total_score_spin.value()
        answer_text = self.subjective_answer_text.toPlainText().strip()
        user_prompt = self.user_prompt_text.toPlainText().strip()
        
        if not answer_text:
            QMessageBox.warning(self, "输入错误", "请输入参考答案")
            return
        
        # 添加到主观题配置
        self.subjective_questions[q_num] = {
            'total_score': total_score,
            'answer': answer_text,
            'user_prompt': user_prompt  # 添加用户提示词
        }
        
        # 更新表格显示
        self.update_subjective_table()
        
        # 清空输入框
        self.subjective_answer_text.clear()
        self.user_prompt_text.clear()  # 清空用户提示词输入框
        self.subj_question_num_spin.setValue(self.subj_question_num_spin.value() + 1)
        
        QMessageBox.information(self, "添加成功", f"已添加第{q_num}题主观题（{total_score}分）")
    
    def update_subjective_table(self):
        """更新主观题表格显示"""
        self.subjective_table.setRowCount(len(self.subjective_questions))
        
        for row, (q_num, q_data) in enumerate(sorted(self.subjective_questions.items())):
            self.subjective_table.setItem(row, 0, QTableWidgetItem(str(q_num)))
            self.subjective_table.setItem(row, 1, QTableWidgetItem(str(q_data['total_score'])))
            # 显示答案的前50个字符
            answer_preview = q_data['answer'][:50] + "..." if len(q_data['answer']) > 50 else q_data['answer']
            self.subjective_table.setItem(row, 2, QTableWidgetItem(answer_preview))
            # 显示用户提示词的前30个字符
            user_prompt = q_data.get('user_prompt', '')
            prompt_preview = user_prompt[:30] + "..." if len(user_prompt) > 30 else user_prompt
            self.subjective_table.setItem(row, 3, QTableWidgetItem(prompt_preview))
    
    def delete_selected_subjective(self):
        """删除选中的主观题"""
        selected_rows = set()
        for item in self.subjective_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请选择要删除的题目")
            return
        
        # 获取要删除的题号
        question_nums_to_delete = []
        for row in selected_rows:
            q_num_item = self.subjective_table.item(row, 0)
            if q_num_item:
                question_nums_to_delete.append(int(q_num_item.text()))
        
        # 删除题目
        for q_num in question_nums_to_delete:
            if q_num in self.subjective_questions:
                del self.subjective_questions[q_num]
        
        # 更新表格
        self.update_subjective_table()
        
        QMessageBox.information(self, "删除成功", f"已删除 {len(question_nums_to_delete)} 道主观题")
    
    def import_subjective_from_file(self):
        """从文件导入主观题配置"""
        path, _ = QFileDialog.getOpenFileName(
            self, '选择主观题答案文件',
            '', '文本文件 (*.txt)'
        )
        if not path:
            return
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 简单解析主观题文件
            lines = content.split('\n')
            current_question = None
            current_answer = []
            current_user_prompt = ""
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # 检查是否是题目行（包含"题"和分数）
                if '题' in line and '分' in line:
                    # 保存上一题
                    if current_question is not None and current_answer:
                        self.subjective_questions[current_question['num']] = {
                            'total_score': current_question['score'],
                            'answer': '\n'.join(current_answer),
                            'user_prompt': current_user_prompt
                        }
                    
                    # 解析新题目
                    import re
                    match = re.search(r'(\d+)题.*?（(\d+(?:\.\d+)?)分）', line)
                    if match:
                        current_question = {
                            'num': int(match.group(1)),
                            'score': float(match.group(2))
                        }
                        current_answer = []
                        current_user_prompt = ""
                elif line.startswith('用户提示词：'):
                    # 解析用户提示词
                    current_user_prompt = line[6:]  # 去掉"用户提示词："前缀
                else:
                    # 答案内容
                    if current_question is not None:
                        current_answer.append(line)
            
            # 保存最后一题
            if current_question is not None and current_answer:
                self.subjective_questions[current_question['num']] = {
                    'total_score': current_question['score'],
                    'answer': '\n'.join(current_answer),
                    'user_prompt': current_user_prompt
                }
            
            self.update_subjective_table()
            QMessageBox.information(self, "导入成功", f"已导入 {len(self.subjective_questions)} 道主观题")
            
        except Exception as e:
            QMessageBox.critical(self, "导入错误", f"文件导入失败：{str(e)}")
    
    def export_subjective_to_file(self):
        """导出主观题配置到文件"""
        if not self.subjective_questions:
            QMessageBox.warning(self, "提示", "没有可导出的主观题")
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self, '保存主观题答案文件',
            'subjective_answer.txt', '文本文件 (*.txt)'
        )
        if not path:
            return
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write("# 主观题答案配置文件\n")
                
                for q_num in sorted(self.subjective_questions.keys()):
                    q_data = self.subjective_questions[q_num]
                    f.write(f"{q_num}题（{q_data['total_score']}分）\n")
                    f.write(f"{q_data['answer']}\n\n")
            
            QMessageBox.information(self, "导出成功", f"已导出到 {path}")
            
        except Exception as e:
            QMessageBox.critical(self, "导出错误", f"文件导出失败：{str(e)}")

    def _setup_api_edit_fields(self):
        self._register_dblclick_edit(self.api_key_input, reveal_api_key=True)
        self._register_dblclick_edit(self.api_base_url_input, reveal_api_key=False)
        self.model_combo.setEditable(True)
        self._model_line_edit = self.model_combo.lineEdit()
        if self._model_line_edit:
            self._register_dblclick_edit(self._model_line_edit, reveal_api_key=False)

    def _register_dblclick_edit(self, line_edit, reveal_api_key=False):
        line_edit.setReadOnly(True)
        line_edit.installEventFilter(self)
        line_edit.editingFinished.connect(
            lambda le=line_edit, reveal=reveal_api_key: self._on_edit_finished(le, reveal)
        )
        self._dblclick_edit_targets[line_edit] = {"reveal_api_key": reveal_api_key}

    def _on_edit_finished(self, line_edit, reveal_api_key=False):
        if reveal_api_key:
            text = line_edit.text().strip()
            if text:
                line_edit.setProperty("original_api_key", text)
                if len(text) > 12:
                    masked_key = text[:6] + "***" + text[-6:]
                else:
                    masked_key = "*" * len(text)
                line_edit.setText(masked_key)
        line_edit.setReadOnly(True)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonDblClick:
            target = self._dblclick_edit_targets.get(obj)
            if target is not None:
                if target.get("reveal_api_key"):
                    current_text = obj.text()
                    original = obj.property("original_api_key")
                    if original and "***" in current_text:
                        obj.setText(original)
                obj.setReadOnly(False)
                obj.setFocus()
                obj.selectAll()
                return True
        return super().eventFilter(obj, event)

    def _get_api_settings_from_inputs(self):
        """从界面控件中提取当前 API 配置"""
        api_key_text = self.api_key_input.text().strip()
        original_api_key = self.api_key_input.property("original_api_key")
        if "***" in api_key_text and original_api_key:
            api_key = str(original_api_key).strip()
        else:
            api_key = api_key_text

        return {
            "api_key": api_key,
            "api_base_url": self.api_base_url_input.text().strip(),
            "model_name": self.model_combo.currentText().strip(),
        }

    def refresh_from_config(self, config, reload_answer_files=False):
        """使用最新配置刷新界面显示"""
        self.current_config = config or {}
        self.load_current_config(reload_answer_files=reload_answer_files)

    def test_api_connection(self):
        """测试当前 API 配置是否可用"""
        api_settings = self._get_api_settings_from_inputs()
        api_key = api_settings["api_key"]
        base_url = api_settings["api_base_url"]
        model_name = api_settings["model_name"]

        if not api_key:
            QMessageBox.warning(self, "提示", "请先输入 API 密钥。")
            return
        if not base_url:
            QMessageBox.warning(self, "提示", "请先输入 API 地址。")
            return
        if not model_name:
            QMessageBox.warning(self, "提示", "请先选择或输入模型名称。")
            return

        try:
            from openai import OpenAI

            QApplication.setOverrideCursor(Qt.WaitCursor)
            client = OpenAI(api_key=api_key, base_url=base_url, timeout=15.0)
            client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
                temperature=0,
            )
            QMessageBox.information(self, "测试成功", "API 密钥、API 地址和模型配置可正常使用。")
        except Exception as e:
            QMessageBox.critical(self, "测试失败", f"当前 API 配置不可用：{str(e)}")
        finally:
            QApplication.restoreOverrideCursor()
    
    def load_current_config(self, reload_answer_files=True):
        """加载当前配置到界面"""
        # 加载API配置
        if self.current_config.get("api_key"):
            # 显示掩码形式的API密钥
            api_key = self.current_config["api_key"]
            if len(api_key) > 12:  # 确保API密钥长度足够
                masked_key = api_key[:6] + "***" + api_key[-6:]
            else:
                masked_key = "*" * len(api_key)
            self.api_key_input.setText(masked_key)
            # 保存原始密钥到属性中
            self.api_key_input.setProperty("original_api_key", api_key)
        else:
            self.api_key_input.clear()
            self.api_key_input.setProperty("original_api_key", "")
        
        if self.current_config.get("api_base_url"):
            self.api_base_url_input.setText(self.current_config["api_base_url"])
        else:
            self.api_base_url_input.setText("https://api.siliconflow.cn/v1")
        
        if self.current_config.get("model_name"):
            # 设置模型选择
            current_model_name = self.current_config["model_name"]
            index = self.model_combo.findText(current_model_name)
            if index < 0 and current_model_name:
                self.model_combo.addItem(current_model_name)
                index = self.model_combo.findText(current_model_name)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)

        if not reload_answer_files:
            return
        
        # 加载客观题配置（从配置文件重新读取）
        try:
            # 使用实例的配置管理器获取最新的配置文件路径
            objective_path = self.config_manager.get_objective_answer_path()
            
            print(f"尝试加载客观题配置文件: {objective_path}")
            
            if os.path.exists(objective_path):
                # 重新解析配置文件
                from core.omr.question_parser import parse_multiple_choice_answers
                answers, scores, options = parse_multiple_choice_answers(objective_path)
                
                print(f"成功解析客观题配置文件，找到 {len(answers)} 道题目")
                
                # 清空现有配置
                self.objective_questions.clear()
                
                # 重新加载配置
                for q_num, answer in answers.items():
                    score = scores.get(q_num, 1.0)
                    # 确保分数保留两位小数精度
                    if isinstance(score, float):
                         score = round(score, 2)
                    
                    self.objective_questions[q_num] = {
                        'type': '单选题' if isinstance(answer, str) else '多选题',
                        'score': score,
                        'answer': answer,
                        'options': options.get(q_num, 4)
                    }
                
                # 更新表格显示
                self.update_questions_table()
                
            else:
                print(f"配置文件不存在: {objective_path}")
                
        except Exception as e:
            print(f"加载客观题配置失败: {e}")
            # 如果文件加载失败，尝试从current_config加载
            if self.current_config.get("objective_answer"):
                try:
                    answer_dict = self.current_config["objective_answer"]
                    self.objective_questions.clear()
                    for q_num, q_data in answer_dict.items():
                        self.objective_questions[q_num] = {
                            'type': '单选题' if isinstance(q_data['answer'], str) else '多选题',
                            'score': q_data['score'],
                            'answer': q_data['answer'],
                            'options': q_data.get('options', 4)
                        }
                    self.update_questions_table()
                except Exception as e2:
                    print(f"从配置字典加载客观题配置也失败: {e2}")
        
        # 加载主观题配置（从配置文件重新读取）
        try:
            # 使用实例的配置管理器获取最新的主观题配置文件路径
            subjective_path = self.config_manager.get_subjective_answer_path()
            
            print(f"尝试加载主观题配置文件: {subjective_path}")
            
            if os.path.exists(subjective_path):
                # 重新解析主观题配置文件
                self.subjective_questions.clear()
                
                with open(subjective_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    
                if content:
                    # 解析主观题配置文件格式
                    sections = content.split('\n\n')
                    for section in sections:
                        if section.strip() and not section.startswith('#'):
                            lines = section.strip().split('\n')
                            if len(lines) >= 2:
                                # 第一行：题号和分数信息
                                header = lines[0].strip()
                                # 提取题号和分数，格式如：1题（10分）
                                import re
                                match = re.match(r'(\d+)题.*?（(\d+(?:\.\d+)?)分）', header)
                                if match:
                                    q_num = int(match.group(1))
                                    total_score = float(match.group(2))
                                    
                                    # 其余行：答案内容
                                    answer_content = '\n'.join(lines[1:]).strip()
                                    
                                    self.subjective_questions[q_num] = {
                                        'total_score': total_score,
                                        'answer': answer_content
                                    }
                
                print(f"成功解析主观题配置文件，找到 {len(self.subjective_questions)} 道题目")
                
                # 更新主观题表格显示
                self.update_subjective_table()
                
            else:
                print(f"主观题配置文件不存在: {subjective_path}")
                
        except Exception as e:
            print(f"加载主观题配置失败: {e}")
            # 如果文件加载失败，尝试从current_config加载
            if self.current_config.get("subjective_answer"):
                try:
                    subjective_data = self.current_config["subjective_answer"]
                    # 这里可以根据需要解析主观题数据
                    # 暂时不自动加载，让用户手动配置
                except Exception as e2:
                    print(f"从配置字典加载主观题配置也失败: {e2}")
        
        # 加载识别模式到识别配置选项卡
        try:
            mode = self.config_manager.get_recognition_mode()
        except Exception:
            mode = "A"
        if hasattr(self, "recognition_mode_combo"):
            self.recognition_mode_combo.setCurrentIndex(1 if mode == "B" else 0)
        # 加载题列布局
        try:
            layout = self.config_manager.get_recognition_layout()
        except Exception:
            layout = "row"
        if hasattr(self, "recognition_layout_combo"):
            self.recognition_layout_combo.setCurrentIndex(1 if layout == "column" else 0)
        # 加载题组数量
        try:
            group_size = self.config_manager.get_recognition_group_size()
        except Exception:
            group_size = 5
        if hasattr(self, "group_size_spin"):
            self.group_size_spin.setValue(group_size)
        # 加载检测置信度阈值
        try:
            conf_thres = self.config_manager.get_recognition_conf_thres()
        except Exception:
            conf_thres = 0.75
        if hasattr(self, "conf_thres_spin"):
            self.conf_thres_spin.setValue(float(conf_thres))
        try:
            scoring_rule = self.config_manager.get_objective_scoring_rule()
        except Exception:
            scoring_rule = "standard"
        if hasattr(self, "objective_scoring_combo"):
            self.objective_scoring_combo.setCurrentIndex(1 if scoring_rule == "partial_penalty" else 0)
    
    def format_answer_preview(self, answer_dict):
        if not answer_dict:
            return ""
        
        preview_text = ""
        for question_num in sorted(answer_dict.keys()):
            item = answer_dict[question_num]
            preview_text += f"题号 {question_num}: 答案={item['answer']}, 分值={item['score']}\n"
        
        return preview_text
    
    def format_subjective_answer_preview(self, answer_data):
        """格式化主观题答案预览 - 直接显示txt文件内容"""
        try:
            # 如果是文件路径，直接读取文件内容
            if isinstance(answer_data, str) and answer_data.endswith('.txt'):
                try:
                    with open(answer_data, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return content
                except Exception as e:
                    return f"无法读取文件: {e}"
            
            # 如果是解析后的字典，也尝试显示原始内容
            elif isinstance(answer_data, dict):
                # 尝试从配置中获取文件路径
                file_path = self.current_config.get("subjective_answer")
                if file_path and isinstance(file_path, str) and file_path.endswith('.txt'):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        return content
                    except Exception as e:
                        return f"无法读取文件: {e}"
                
                # 如果无法获取原始文件，显示解析后的内容
                preview_lines = []
                for q_num, q_data in answer_data.items():
                    preview_lines.append(f"题目 {q_num}: 总分 {q_data['score']} 分")
                    if 'answer' in q_data:
                        answer_text = q_data['answer'][:100] + "..." if len(q_data['answer']) > 100 else q_data['answer']
                        preview_lines.append(f"答案: {answer_text}")
                    if 'sub_questions' in q_data:
                        preview_lines.append(f"子题数量: {len(q_data['sub_questions'])}")
                    preview_lines.append("")
                return "\n".join(preview_lines)
            
            else:
                return "无效的答案数据格式"
                
        except Exception as e:
            return f"预览生成失败: {e}"
    
    
    def browse_objective_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, '选择客观题答案文件',
            '', '文本文件 (*.txt)'
        )
        if not path:
            return
        
        self.objective_file_path.setText(path)
        try:
            # 使用主窗口的解析方法
            answer_dict = self._parse_objective_answer_file(path)
            self.current_config["objective_answer"] = answer_dict
            self.objective_preview.setText(self.format_answer_preview(answer_dict))
            # 保存文件路径到主窗口，以便后续保存到配置管理器
            self.parent()._last_objective_path = path
        except Exception as e:
            QMessageBox.critical(self, "解析错误", f"客观题答案文件解析失败：{str(e)}")
    
    def save_config(self):
        try:
            # 保存客观题配置
            if self.objective_questions:
                # 生成客观题答案文件
                from utils.path_utils import get_config_file_path, ensure_dir_exists
                objective_path = get_config_file_path('objective_answer.txt')
                ensure_dir_exists(objective_path)
                
                with open(objective_path, 'w', encoding='utf-8') as f:
                    f.write("# 客观题答案配置文件\n")
                    f.write("# 格式：题号:答案:分值:选项个数\n\n")
                    
                    for q_num in sorted(self.objective_questions.keys()):
                        q_data = self.objective_questions[q_num]
                        answer = q_data['answer']
                        score = q_data['score']
                        options = q_data.get('options', 4)  # 默认4个选项
                        
                        if isinstance(answer, list):
                            answer_str = ','.join(answer)
                        else:
                            answer_str = str(answer)
                        
                        f.write(f"{q_num}:{answer_str}:{score}:{options}\n")
                
                # 更新配置文件路径到配置管理器（使用相对路径）
                from utils.config_manager import config_manager
                config_manager.update({
                    'objective_answer_path': 'config\\answer_config\\objective_answer.txt'
                })
                
                # 更新当前配置：保存的文件路径与解析后的客观题答案字典
                self.current_config['objective_answer_file'] = objective_path
                try:
                    # 解析刚保存的文件，确保传入评分流程的是最新一致的字典结构
                    self.current_config['objective_answer'] = self._parse_objective_answer_file(objective_path)
                    # 同步答案文件路径，供主窗口传递给 omr_processor 使用
                    self.current_config['answer_config_file'] = objective_path
                except Exception as e:
                    print(f"解析保存后的客观题配置失败: {e}")
            
            # 保存主观题配置
            if self.subjective_questions:
                subjective_path = get_config_file_path('subjective_answer.txt')
                ensure_dir_exists(subjective_path)
                
                with open(subjective_path, 'w', encoding='utf-8') as f:
                    f.write("# 主观题答案配置文件\n\n")
                    
                    for q_num in sorted(self.subjective_questions.keys()):
                        q_data = self.subjective_questions[q_num]
                        f.write(f"{q_num}题（{q_data['total_score']}分）\n")
                        f.write(f"{q_data['answer']}\n")
                        # 保存用户提示词（如果存在）
                        if q_data.get('user_prompt'):
                            f.write(f"用户提示词：{q_data['user_prompt']}\n")
                        f.write("\n")
                
                # 更新配置文件路径到配置管理器（使用相对路径）
                from utils.config_manager import config_manager
                config_manager.update({
                    'subjective_answer_path': 'config\\answer_config\\subjective_answer.txt'
                })
                
                # 更新当前配置
                self.current_config['subjective_answer_file'] = subjective_path
            
            # 保存题型配置
            # if self.objective_questions:
            #     question_types_path = get_config_file_path('question_types.txt')
            #     ensure_dir_exists(question_types_path)
            #     
            #     with open(question_types_path, 'w', encoding='utf-8') as f:
            #         f.write("# 题目类型配置文件\n")
            #         f.write("# 格式：题号:类型 或 起始题号-结束题号:类型\n")
            #         f.write("# 类型：single(单选题) 或 multiple(多选题)\n\n")
            #         
            #         # 按题号排序并生成配置
            #         sorted_questions = sorted(self.objective_questions.keys())
            #         if sorted_questions:
            #             # 按类型分组连续的题号
            #             current_type = self.objective_questions[sorted_questions[0]]['type']
            #             start_num = sorted_questions[0]
            #             end_num = sorted_questions[0]
            #             
            #             for i in range(1, len(sorted_questions)):
            #                 q_num = sorted_questions[i]
            #                 q_type = self.objective_questions[q_num]['type']
            #                 
            #                 if q_type == current_type and q_num == end_num + 1:
            #                     # 连续且同类型，扩展范围
            #                     end_num = q_num
            #                 else:
            #                     # 不连续或类型不同，写入当前范围
            #                     type_str = 'single' if current_type == '单选题' else 'multiple'
            #                     if start_num == end_num:
            #                         f.write(f"{start_num}:{type_str}\n")
            #                     else:
            #                         f.write(f"{start_num}-{end_num}:{type_str}\n")
            #                     
            #                     # 开始新的范围
            #                     current_type = q_type
            #                     start_num = q_num
            #                     end_num = q_num
            #             
            #             # 写入最后一个范围
            #             type_str = 'single' if current_type == '单选题' else 'multiple'
            #             if start_num == end_num:
            #                 f.write(f"{start_num}:{type_str}\n")
            #             else:
            #                 f.write(f"{start_num}-{end_num}:{type_str}\n")
            #     
            #     # 更新配置文件路径到配置管理器（使用相对路径）
            #     config_manager.update({
            #         'question_types_path': 'answer_config\\question_types.txt'
            #     })
            
            # 获取API密钥
            api_key_text = self.api_key_input.text().strip()

            # 检查是否是掩码形式的API密钥
            if "***" in api_key_text and hasattr(self.api_key_input, "property") and self.api_key_input.property(
                    "original_api_key"):
                # 如果是掩码形式且存在原始密钥，使用原始密钥
                self.current_config["api_key"] = self.api_key_input.property("original_api_key")
            else:
                # 如果是新输入的密钥（包括空字符串），直接使用
                self.current_config["api_key"] = api_key_text
                if api_key_text:
                     QMessageBox.warning(self, "密钥更新", "api key已更新！")

            # 保存API基础URL
            self.current_config["api_base_url"] = self.api_base_url_input.text().strip()
            
            # 保存模型配置
            model_name = self.model_combo.currentText().strip()
            if model_name:
                self.current_config["model_name"] = model_name
                existing_models = self.current_config.get("available_models", [])
                if model_name not in existing_models:
                    self.current_config["available_models"] = existing_models + [model_name]

            # 保存识别模式配置
            if hasattr(self, "recognition_mode_combo"):
                idx = self.recognition_mode_combo.currentIndex()
                selected_mode = "B" if idx == 1 else "A"
                try:
                    self.config_manager.set_recognition_mode(selected_mode)
                except Exception as e:
                    print(f"保存识别模式失败: {e}")
                # 也写入当前配置，供父窗口同步
                self.current_config["recognition_mode"] = selected_mode

            # 保存题列布局配置
            if hasattr(self, "recognition_layout_combo"):
                idx_layout = self.recognition_layout_combo.currentIndex()
                selected_layout = "column" if idx_layout == 1 else "row"
                try:
                    self.config_manager.set_recognition_layout(selected_layout)
                except Exception as e:
                    print(f"保存题列布局失败: {e}")
                # 写入当前配置，供父窗口同步
                self.current_config["recognition_layout"] = selected_layout

            # 保存题组数量（每图题数）
            if hasattr(self, "group_size_spin"):
                selected_size = int(self.group_size_spin.value())
                try:
                    self.config_manager.set_recognition_group_size(selected_size)
                except Exception as e:
                    print(f"保存题组数量失败: {e}")
                # 写入当前配置，供父窗口同步
                self.current_config["recognition_group_size"] = selected_size

            # 保存检测置信度阈值
            if hasattr(self, "conf_thres_spin"):
                selected_conf = float(self.conf_thres_spin.value())
                try:
                    self.config_manager.set_recognition_conf_thres(selected_conf)
                except Exception as e:
                    print(f"保存置信度阈值失败: {e}")
                # 写入当前配置，供父窗口同步
                self.current_config["recognition_conf_thres"] = selected_conf

            if hasattr(self, "objective_scoring_combo"):
                idx_rule = self.objective_scoring_combo.currentIndex()
                selected_rule = "partial_penalty" if idx_rule == 1 else "standard"
                try:
                    self.config_manager.set_objective_scoring_rule(selected_rule)
                except Exception as e:
                    print(f"保存评分规则失败: {e}")
                self.current_config["objective_scoring_rule"] = selected_rule

            # 发送配置保存信号
            self.config_saved.emit(self.current_config)
            
            QMessageBox.information(self, "保存成功", "配置已保存")
            # 作为主界面嵌入组件时，不应关闭；仅在独立弹窗模式下关闭
            if self.isWindow():
                self.accept()
            else:
                self.setVisible(True)
                self.raise_()
            
        except Exception as e:
            QMessageBox.critical(self, "保存错误", f"配置保存失败：{str(e)}")

class OMRGUI(QMainWindow):
    answer_config_loaded = Signal(dict)

    def __init__(self):
        super().__init__()
        self.single_file_path = None
        self.batch_folder_path = None
        self.student_info = StudentInfo()
        self.answer_key = {}
        self.current_results = []
        self.current_file_index = 0
        self.total_files = 0

        # 添加系统配置 - 使用配置管理器
        self.system_config = {
            "objective_answer": {},
            "subjective_answer": {},
            "question_types": {},
            "api_key": config_manager.get_api_key(),
            "api_base_url": config_manager.get("api_base_url", "https://api.siliconflow.cn/v1"),
            "model_name": config_manager.get("model_name", "Qwen/Qwen3-VL-30B-A3B-Instruct"),
            "available_models": config_manager.get("available_models", []),
            "answer_config_file": ""  # 答案配置文件路径
        }
        
        # 初始化配置数据
        self.subjective_questions = {}  # 主观题配置
        
        # 初始化新功能的属性
        # 从系统配置加载识别模式（A/B）
        try:
            self.recognition_mode = config_manager.get_recognition_mode()
        except Exception:
            self.recognition_mode = "A"  # 兜底
        self.enable_subjective = True  # 默认开启主观题评分
        self.enable_objective = True  # 默认开启客观题阅卷
        self.enable_student_info = True  # 默认开启学生信息识别
        self.enable_barcode = False  # 默认关闭条形码识别
        
        self.smart_agent_dialog = None # 智能助手对话框实例


        # 检查激活状态
        self.activation_manager = ActivationManager()
        # main.py 已处理激活/试用检查，此处不再重复检查
        self.initUI()
        self.apply_stylesheet()
        # 启动时自动加载配置
        self.auto_load_config()

        # 如果是试用模式，可以在标题栏显示提示（可选）
        is_trial, msg, days = self.activation_manager.check_trial_status()
        if not self.activation_manager.is_activated() and is_trial:
             self.setWindowTitle(f'智能答题卡批改系统 (试用版 - 剩余 {days} 天)')

    def initUI(self):
        self.setWindowTitle('智能答题卡批改系统')
        self.setGeometry(100, 100, 1280, 720)

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        self.setCentralWidget(main_widget)

        title_label = QLabel('智能答题卡批改系统')
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont('Microsoft YaHei', 20, QFont.Bold))
        title_label.setStyleSheet("""
            color: #1E293B; 
            margin-bottom: 8px;
            padding: 10px 14px;
            background: #FFFFFF;
            border: 1px solid #E8EDF5;
            border-radius: 12px;
            font-weight: 700;
        """)
        main_layout.addWidget(title_label)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(10)
        main_layout.addLayout(content_layout, 1)

        nav_widget = QWidget()
        nav_widget.setFixedWidth(178)
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 4, 0, 4)
        nav_layout.setSpacing(6)

        self.btn_nav_marking = QPushButton("🧾  阅卷中心")
        self.btn_nav_trace = QPushButton("🖼️  阅卷痕迹")
        self.btn_nav_reports = QPushButton("📄  阅卷报告")
        self.btn_nav_stats = QPushButton("📊  数据统计")
        self.btn_nav_settings = QPushButton("⚙️  参数设置")
        self.btn_toggle_assistant = QPushButton("🤖 隐藏助手")
        for nav_btn in [self.btn_nav_marking, self.btn_nav_trace, self.btn_nav_reports, self.btn_nav_stats, self.btn_nav_settings, self.btn_toggle_assistant]:
            nav_btn.setMinimumHeight(40)
            nav_btn.setCursor(Qt.PointingHandCursor)
            nav_btn.setStyleSheet("text-align: left; padding-left: 12px; border-radius: 10px; font-size: 13px; font-weight: 600;")
            nav_layout.addWidget(nav_btn)
        nav_layout.addStretch()
        content_layout.addWidget(nav_widget)

        primary_button_style = """
            QPushButton {
                background: #2563EB;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                font-weight: 600;
                font-size: 12px;
                min-height: 16px;
            }
            QPushButton:hover {
                background: #1D4ED8;
            }
            QPushButton:pressed {
                background: #1E40AF;
            }
            QPushButton:disabled {
                background-color: #BDC3C7;
                color: #7F8C8D;
            }
        """
        
        secondary_button_style = """
            QPushButton {
                background: #FFFFFF;
                color: #334155;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 8px 12px;
                font-weight: 600;
                font-size: 12px;
                min-height: 16px;
            }
            QPushButton:hover {
                background: #F8FAFC;
            }
            QPushButton:pressed {
                background: #E2E8F0;
            }
        """
        
        accent_button_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FF6B6B, stop:1 #E55A5A);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                font-weight: 600;
                font-size: 12px;
                min-height: 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FF7B7B, stop:1 #FF6B6B);
            }
            QPushButton:pressed {
                background: #E55A5A;
            }
        """
        
        warning_button_style = """
            QPushButton {
                background: #FFFFFF;
                color: #334155;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 8px 12px;
                font-weight: 600;
                font-size: 12px;
                min-height: 16px;
            }
            QPushButton:hover {
                background: #F8FAFC;
            }
            QPushButton:pressed {
                background: #E2E8F0;
            }
        """
        
        toggle_off_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #95A5A6, stop:1 #7F8C8D);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                font-weight: 600;
                font-size: 12px;
                min-height: 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #A5B5B6, stop:1 #95A5A6);
            }
            QPushButton:pressed {
                background: #7F8C8D;
            }
        """

        self.chk_objective = QCheckBox('阅卷客观题')
        self.chk_subjective = QCheckBox('阅卷主观题')
        self.chk_student_info = QCheckBox('识别学生信息')
        self.chk_barcode = QCheckBox('识别条形码')
        self.lbl_objective_state = QLabel()
        self.lbl_subjective_state = QLabel()
        self.lbl_student_info_state = QLabel()
        self.lbl_barcode_state = QLabel()
        for state_label in [self.lbl_objective_state, self.lbl_subjective_state, self.lbl_student_info_state, self.lbl_barcode_state]:
            state_label.setAlignment(Qt.AlignCenter)
            state_label.setMinimumWidth(36)
        self.chk_objective.setChecked(self.enable_objective)
        self.chk_subjective.setChecked(self.enable_subjective)
        self.chk_student_info.setChecked(self.enable_student_info)
        self.chk_barcode.setChecked(self.enable_barcode)

        self.btn_file = QPushButton('📁 选择单个文件')
        self.btn_file.setStyleSheet(secondary_button_style)
        self.btn_batch = QPushButton('📂 选择批量处理文件夹')
        self.btn_batch.setStyleSheet(secondary_button_style)
        self.btn_recognition = QPushButton('🚀 开始识别')
        self.btn_recognition.setStyleSheet(secondary_button_style)
        self.btn_export = QPushButton('📊 导出成绩')
        self.btn_export.setStyleSheet(warning_button_style)
        for action_btn in [self.btn_file, self.btn_batch, self.btn_recognition, self.btn_export]:
            action_btn.setMinimumHeight(32)

        self.primary_style = primary_button_style
        self.secondary_style = secondary_button_style
        self.accent_style = accent_button_style
        self.warning_style = warning_button_style
        self.toggle_off_style = toggle_off_style
        self.nav_active_style = """
            QPushButton {
                background-color: #1E66F5;
                color: white;
                border: none;
                border-radius: 10px;
                text-align: left;
                padding-left: 12px;
                font-size: 13px;
                font-weight: 700;
            }
        """
        self.nav_inactive_style = """
            QPushButton {
                background-color: #FFFFFF;
                color: #334155;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                text-align: left;
                padding-left: 12px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
            }
        """
        for nav_btn in [self.btn_nav_marking, self.btn_nav_trace, self.btn_nav_reports, self.btn_nav_stats, self.btn_nav_settings, self.btn_toggle_assistant]:
            nav_btn.setStyleSheet(self.nav_inactive_style)

        self.main_stack = QStackedWidget()
        content_layout.addWidget(self.main_stack, 1)

        marking_page = QWidget()
        marking_layout = QVBoxLayout(marking_page)
        marking_layout.setContentsMargins(0, 0, 0, 0)

        control_group = QGroupBox("阅卷配置")
        control_layout = QGridLayout(control_group)
        control_layout.setHorizontalSpacing(10)
        control_layout.setVerticalSpacing(8)
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(10)
        buttons_row.addWidget(self.btn_file)
        buttons_row.addWidget(self.btn_batch)
        buttons_row.addWidget(self.btn_recognition)
        buttons_row.addWidget(self.btn_export)
        control_layout.addLayout(buttons_row, 0, 0, 1, 2)
        flags_row = QHBoxLayout()
        flags_row.setSpacing(18)
        flags_row.addWidget(self._create_flag_item(self.chk_objective, self.lbl_objective_state))
        flags_row.addWidget(self._create_flag_item(self.chk_subjective, self.lbl_subjective_state))
        flags_row.addWidget(self._create_flag_item(self.chk_student_info, self.lbl_student_info_state))
        flags_row.addWidget(self._create_flag_item(self.chk_barcode, self.lbl_barcode_state))
        flags_row.addStretch()
        control_layout.addLayout(flags_row, 1, 0, 1, 2)
        marking_layout.addWidget(control_group)

        selection_group = QGroupBox("已选择源")
        selection_layout = QVBoxLayout(selection_group)
        self.selected_source_label = QLabel("未选择文件或文件夹")
        self.selected_items_list = QListWidget()
        selection_layout.addWidget(self.selected_source_label)
        selection_layout.addWidget(self.selected_items_list)
        marking_layout.addWidget(selection_group)

        marking_splitter = QSplitter(Qt.Horizontal)
        preview_group = QGroupBox("答题卡预览")
        preview_layout = QVBoxLayout(preview_group)
        self.image_label = QLabel('📷 请选择图片或文件夹')
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(500, 320)
        self.image_label.setStyleSheet("""
            border: 2px dashed #4A90E2; 
            border-radius: 10px; 
            background-color: #F8F9FA; 
            padding: 20px;
            color: #6C757D;
            font-size: 16px;
            font-weight: 500;
        """)
        preview_layout.addWidget(self.image_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("📊 %v/%m (%p%)")
        preview_layout.addWidget(self.progress_bar)
        self.status_label = QLabel('✨ 准备就绪')
        self.status_label.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(self.status_label)
        marking_splitter.addWidget(preview_group)

        table_group = QGroupBox("识别结果与联动预览")
        table_layout = QVBoxLayout(table_group)
        self.result_table = self.create_result_table()
        table_layout.addWidget(self.result_table, 3)
        linked_group = QGroupBox("报告与阅卷痕迹联动")
        linked_layout = QHBoxLayout(linked_group)
        self.linked_files_list = QListWidget()
        self.linked_files_list.setMinimumWidth(220)
        self.linked_preview_tabs = QTabWidget()
        self.linked_preview_text = QTextEdit()
        self.linked_preview_text.setReadOnly(True)
        self.linked_preview_text.setPlaceholderText("选择结果行后，将展示匹配到的报告内容或阅卷痕迹文件")
        self.linked_preview_image = QLabel("暂无图片预览")
        self.linked_preview_image.setAlignment(Qt.AlignCenter)
        self.linked_preview_image.setMinimumHeight(180)
        self.linked_preview_tabs.addTab(self.linked_preview_text, "文本预览")
        self.linked_preview_tabs.addTab(self.linked_preview_image, "图片预览")
        linked_layout.addWidget(self.linked_files_list, 1)
        linked_layout.addWidget(self.linked_preview_tabs, 2)
        table_layout.addWidget(linked_group, 2)
        marking_splitter.addWidget(table_group)
        marking_splitter.setSizes([int(self.width() * 0.55), int(self.width() * 0.45)])
        marking_layout.addWidget(marking_splitter, 1)

        trace_page = QWidget()
        trace_layout = QVBoxLayout(trace_page)
        trace_top = QHBoxLayout()
        self.trace_summary_label = QLabel("read 目录痕迹文件")
        self.btn_refresh_trace = QPushButton("🔄 刷新痕迹")
        self.btn_refresh_trace.setStyleSheet(primary_button_style)
        trace_top.addWidget(self.trace_summary_label, 1)
        trace_top.addWidget(self.btn_refresh_trace)
        trace_layout.addLayout(trace_top)
        trace_splitter = QSplitter(Qt.Horizontal)
        self.trace_table = QTableWidget()
        self.trace_table.setColumnCount(4)
        self.trace_table.setHorizontalHeaderLabels(["文件名", "大小(KB)", "修改时间", "路径"])
        self.trace_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        trace_splitter.addWidget(self.trace_table)
        trace_preview_group = QGroupBox("痕迹预览")
        trace_preview_layout = QVBoxLayout(trace_preview_group)
        self.trace_preview_tabs = QTabWidget()
        self.trace_preview_text = QTextEdit()
        self.trace_preview_text.setReadOnly(True)
        self.trace_preview_image = QLabel("暂无图片预览")
        self.trace_preview_image.setAlignment(Qt.AlignCenter)
        self.trace_preview_tabs.addTab(self.trace_preview_text, "文本预览")
        self.trace_preview_tabs.addTab(self.trace_preview_image, "图片预览")
        trace_preview_layout.addWidget(self.trace_preview_tabs)
        trace_splitter.addWidget(trace_preview_group)
        trace_splitter.setSizes([int(self.width() * 0.62), int(self.width() * 0.38)])
        trace_layout.addWidget(trace_splitter, 1)

        reports_page = QWidget()
        reports_layout = QVBoxLayout(reports_page)
        reports_top = QHBoxLayout()
        self.reports_summary_label = QLabel("reports 目录报告文件")
        self.btn_refresh_reports = QPushButton("🔄 刷新报告")
        self.btn_refresh_reports.setStyleSheet(primary_button_style)
        reports_top.addWidget(self.reports_summary_label, 1)
        reports_top.addWidget(self.btn_refresh_reports)
        reports_layout.addLayout(reports_top)
        reports_splitter = QSplitter(Qt.Horizontal)
        self.reports_only_table = QTableWidget()
        self.reports_only_table.setColumnCount(4)
        self.reports_only_table.setHorizontalHeaderLabels(["文件名", "大小(KB)", "修改时间", "路径"])
        self.reports_only_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        reports_splitter.addWidget(self.reports_only_table)
        reports_preview_group = QGroupBox("报告预览")
        reports_preview_layout = QVBoxLayout(reports_preview_group)
        self.reports_preview_tabs = QTabWidget()
        self.reports_preview_text = QTextEdit()
        self.reports_preview_text.setReadOnly(True)
        self.reports_preview_image = QLabel("暂无图片预览")
        self.reports_preview_image.setAlignment(Qt.AlignCenter)
        self.reports_preview_tabs.addTab(self.reports_preview_text, "文本预览")
        self.reports_preview_tabs.addTab(self.reports_preview_image, "图片预览")
        reports_preview_layout.addWidget(self.reports_preview_tabs)
        reports_splitter.addWidget(reports_preview_group)
        reports_splitter.setSizes([int(self.width() * 0.62), int(self.width() * 0.38)])
        reports_layout.addWidget(reports_splitter, 1)

        stats_page = QWidget()
        stats_layout = QVBoxLayout(stats_page)
        stats_cards_layout = QHBoxLayout()
        self.stat_card_read_count = QLabel("0")
        self.stat_card_reports_count = QLabel("0")
        self.stat_card_total_size = QLabel("0 MB")
        self.stat_bar_read = QProgressBar()
        self.stat_bar_reports = QProgressBar()
        self.stat_bar_size = QProgressBar()
        for title, value_label, progress_bar in [
            ("read 文件数", self.stat_card_read_count, self.stat_bar_read),
            ("reports 文件数", self.stat_card_reports_count, self.stat_bar_reports),
            ("总文件体积", self.stat_card_total_size, self.stat_bar_size),
        ]:
            card = QGroupBox(title)
            card_layout = QVBoxLayout(card)
            value_label.setAlignment(Qt.AlignCenter)
            value_label.setFont(QFont('Microsoft YaHei', 16, QFont.Bold))
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)
            card_layout.addWidget(value_label)
            card_layout.addWidget(progress_bar)
            stats_cards_layout.addWidget(card)
        stats_layout.addLayout(stats_cards_layout)
        stats_top_layout = QHBoxLayout()
        self.stats_summary_label = QLabel("统计加载中...")
        self.btn_refresh_stats = QPushButton("🔄 刷新统计")
        self.btn_refresh_stats.setStyleSheet(primary_button_style)
        stats_top_layout.addWidget(self.stats_summary_label, 1)
        stats_top_layout.addWidget(self.btn_refresh_stats)
        stats_layout.addLayout(stats_top_layout)
        stats_tabs = QTabWidget()
        self.read_table = QTableWidget()
        self.read_table.setColumnCount(4)
        self.read_table.setHorizontalHeaderLabels(["文件名", "大小(KB)", "修改时间", "路径"])
        self.read_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.reports_table = QTableWidget()
        self.reports_table.setColumnCount(4)
        self.reports_table.setHorizontalHeaderLabels(["文件名", "大小(KB)", "修改时间", "路径"])
        self.reports_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        stats_tabs.addTab(self.read_table, "read 目录")
        stats_tabs.addTab(self.reports_table, "reports 目录")
        stats_splitter = QSplitter(Qt.Horizontal)
        stats_splitter.addWidget(stats_tabs)
        stats_preview_group = QGroupBox("统计文件预览")
        stats_preview_layout = QVBoxLayout(stats_preview_group)
        self.stats_preview_text = QTextEdit()
        self.stats_preview_text.setReadOnly(True)
        self.stats_preview_text.setPlaceholderText("点击统计表中的文件可在此预览")
        self.stats_preview_image = QLabel("暂无图片预览")
        self.stats_preview_image.setAlignment(Qt.AlignCenter)
        self.stats_preview_image.setMinimumHeight(220)
        self.stats_preview_tabs = QTabWidget()
        self.stats_preview_tabs.addTab(self.stats_preview_text, "文本预览")
        self.stats_preview_tabs.addTab(self.stats_preview_image, "图片预览")
        stats_preview_layout.addWidget(self.stats_preview_tabs)
        stats_splitter.addWidget(stats_preview_group)
        stats_splitter.setSizes([int(self.width() * 0.65), int(self.width() * 0.35)])
        stats_layout.addWidget(stats_splitter, 1)

        settings_page = QWidget()
        settings_layout = QVBoxLayout(settings_page)
        self.system_config_panel = SystemConfigDialog(self, self.system_config)
        self.system_config_panel.setWindowFlags(Qt.Widget)
        self.system_config_panel.config_saved.connect(self.on_config_saved)
        settings_layout.addWidget(self.system_config_panel)

        self.main_stack.addWidget(marking_page)
        self.main_stack.addWidget(trace_page)
        self.main_stack.addWidget(reports_page)
        self.main_stack.addWidget(stats_page)
        self.main_stack.addWidget(settings_page)

        self.assistant_panel = QGroupBox("智能助手")
        self.assistant_panel.setMinimumWidth(360)
        assistant_layout = QVBoxLayout(self.assistant_panel)
        assistant_header = QHBoxLayout()
        self.assistant_state_label = QLabel("右侧助手已启用")
        self.btn_hide_assistant = QPushButton("隐藏")
        self.btn_hide_assistant.setStyleSheet(primary_button_style)
        assistant_header.addWidget(self.assistant_state_label, 1)
        assistant_header.addWidget(self.btn_hide_assistant)
        assistant_layout.addLayout(assistant_header)
        if self.smart_agent_dialog is None:
            self.smart_agent_dialog = SmartAgentDialog(self)
            self.smart_agent_dialog.config_applied.connect(self.on_smart_agent_config_applied)
        self.smart_agent_dialog.setWindowFlags(Qt.Widget)
        assistant_layout.addWidget(self.smart_agent_dialog, 1)
        content_layout.addWidget(self.assistant_panel)

        self.statusBar().setStyleSheet("background-color: #f5f5f5; color: #2c3e50;")

        self.btn_file.clicked.connect(self.load_single_file)
        self.btn_batch.clicked.connect(self.load_batch_folder)
        self.chk_subjective.stateChanged.connect(self.toggle_subjective_grading)
        self.chk_objective.stateChanged.connect(self.toggle_objective_grading)
        self.chk_student_info.stateChanged.connect(self.toggle_student_info_recognition)
        self.chk_barcode.stateChanged.connect(self.toggle_barcode_recognition)
        self.btn_recognition.clicked.connect(self.start_processing)
        self.btn_export.clicked.connect(self.export_data)
        self.btn_nav_marking.clicked.connect(lambda: self.switch_main_page(0))
        self.btn_nav_trace.clicked.connect(lambda: self.switch_main_page(1))
        self.btn_nav_reports.clicked.connect(lambda: self.switch_main_page(2))
        self.btn_nav_stats.clicked.connect(lambda: self.switch_main_page(3))
        self.btn_nav_settings.clicked.connect(lambda: self.switch_main_page(4))
        self.btn_toggle_assistant.clicked.connect(self.toggle_assistant_panel)
        self.btn_hide_assistant.clicked.connect(self.toggle_assistant_panel)
        self.btn_refresh_stats.clicked.connect(self.refresh_statistics_view)
        self.btn_refresh_trace.clicked.connect(self.refresh_trace_view)
        self.btn_refresh_reports.clicked.connect(self.refresh_reports_view)
        self.result_table.itemSelectionChanged.connect(self.refresh_linked_preview_for_selected_result)
        self.linked_files_list.itemSelectionChanged.connect(self.preview_selected_linked_file)
        self.read_table.itemSelectionChanged.connect(self.preview_selected_stats_file)
        self.reports_table.itemSelectionChanged.connect(self.preview_selected_stats_file)
        self.trace_table.itemSelectionChanged.connect(self.preview_selected_trace_file)
        self.reports_only_table.itemSelectionChanged.connect(self.preview_selected_report_file)

        self.update_switch_status_labels()
        self.switch_main_page(0)
        self.refresh_trace_view()
        self.refresh_reports_view()
        self.refresh_statistics_view()

    def _create_flag_item(self, checkbox, state_label):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(checkbox)
        layout.addWidget(state_label)
        return container

    def _set_switch_state_label(self, label_widget, enabled):
        if enabled:
            label_widget.setText("ON")
            label_widget.setStyleSheet("color: #166534; background: #DCFCE7; border: 1px solid #86EFAC; border-radius: 6px; padding: 1px 6px; font-size: 11px; font-weight: 600;")
        else:
            label_widget.setText("OFF")
            label_widget.setStyleSheet("color: #64748B; background: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 6px; padding: 1px 6px; font-size: 11px; font-weight: 600;")

    def update_switch_status_labels(self):
        self._set_switch_state_label(self.lbl_objective_state, self.chk_objective.isChecked())
        self._set_switch_state_label(self.lbl_subjective_state, self.chk_subjective.isChecked())
        self._set_switch_state_label(self.lbl_student_info_state, self.chk_student_info.isChecked())
        self._set_switch_state_label(self.lbl_barcode_state, self.chk_barcode.isChecked())

    def switch_main_page(self, index):
        self.main_stack.setCurrentIndex(index)
        nav_buttons = [self.btn_nav_marking, self.btn_nav_trace, self.btn_nav_reports, self.btn_nav_stats, self.btn_nav_settings]
        for i, button in enumerate(nav_buttons):
            if i == index:
                button.setStyleSheet(self.nav_active_style)
            else:
                button.setStyleSheet(self.nav_inactive_style)

    def toggle_assistant_panel(self):
        visible = not self.assistant_panel.isVisible()
        self.assistant_panel.setVisible(visible)
        if visible:
            self.btn_toggle_assistant.setText("🤖 隐藏助手")
            self.btn_hide_assistant.setText("隐藏")
            self.assistant_state_label.setText("右侧助手已启用")
        else:
            self.btn_toggle_assistant.setText("🤖 显示助手")
            self.assistant_state_label.setText("右侧助手已隐藏")

    def refresh_statistics_view(self):
        read_dir = os.path.join(os.getcwd(), "read")
        reports_dir = os.path.join(os.getcwd(), "reports")
        read_count, read_size_kb = self._populate_stats_table(self.read_table, read_dir)
        reports_count, reports_size_kb = self._populate_stats_table(self.reports_table, reports_dir)
        total_size_kb = read_size_kb + reports_size_kb
        total_count = max(read_count + reports_count, 1)
        self.stat_card_read_count.setText(str(read_count))
        self.stat_card_reports_count.setText(str(reports_count))
        self.stat_card_total_size.setText(f"{total_size_kb / 1024.0:.2f} MB")
        self.stat_bar_read.setValue(int(100 * read_count / total_count))
        self.stat_bar_reports.setValue(int(100 * reports_count / total_count))
        size_denominator = max(total_size_kb, 1.0)
        self.stat_bar_size.setValue(int(100 * reports_size_kb / size_denominator))
        self.stats_summary_label.setText(
            f"read 文件: {read_count} ({read_size_kb/1024.0:.2f}MB) | "
            f"reports 文件: {reports_count} ({reports_size_kb/1024.0:.2f}MB)"
        )
        self.refresh_trace_view()
        self.refresh_reports_view()
    
    def refresh_trace_view(self):
        trace_dir = os.path.join(os.getcwd(), "read")
        trace_count, trace_size_kb = self._populate_stats_table(self.trace_table, trace_dir)
        self.trace_summary_label.setText(f"痕迹文件: {trace_count} | 体积: {trace_size_kb/1024.0:.2f} MB")

    def refresh_reports_view(self):
        reports_dir = os.path.join(os.getcwd(), "reports")
        report_count, report_size_kb = self._populate_stats_table(self.reports_only_table, reports_dir)
        self.reports_summary_label.setText(f"报告文件: {report_count} | 体积: {report_size_kb/1024.0:.2f} MB")

    def _populate_stats_table(self, table_widget, folder_path):
        table_widget.setRowCount(0)
        if not os.path.exists(folder_path):
            return 0, 0.0
        file_entries = []
        total_size_kb = 0.0
        for root, _, files in os.walk(folder_path):
            for name in files:
                full_path = os.path.join(root, name)
                try:
                    stat = os.stat(full_path)
                    size_kb = stat.st_size / 1024.0
                    modified = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
                    file_entries.append((name, f"{size_kb:.2f}", modified, full_path))
                    total_size_kb += size_kb
                except Exception:
                    continue
        file_entries.sort(key=lambda x: x[2], reverse=True)
        for row, entry in enumerate(file_entries):
            table_widget.insertRow(row)
            for col, text in enumerate(entry):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter if col < 3 else Qt.AlignLeft | Qt.AlignVCenter)
                if col == 0:
                    item.setData(Qt.UserRole, entry[3])
                table_widget.setItem(row, col, item)
        return len(file_entries), total_size_kb

    def refresh_linked_preview_for_selected_result(self):
        self.linked_files_list.clear()
        row = self.result_table.currentRow()
        if row < 0:
            return
        student_id_item = self.result_table.item(row, 0)
        student_name_item = self.result_table.item(row, 1)
        student_id = student_id_item.text().strip() if student_id_item else ""
        student_name = student_name_item.text().strip() if student_name_item else ""
        source_image_path = student_id_item.data(Qt.UserRole) if student_id_item else ""
        files = self._find_related_files(student_id, student_name, source_image_path)
        if not files:
            self.linked_preview_text.setPlainText("未找到与该学生关联的报告或阅卷痕迹文件")
            self.linked_preview_image.setText("暂无图片预览")
            return
        for path in files:
            self.linked_files_list.addItem(path)
        self.linked_files_list.setCurrentRow(0)

    def preview_selected_linked_file(self):
        if not self.linked_files_list.selectedItems():
            return
        selected_path = self.linked_files_list.selectedItems()[0].text()
        self._preview_file(selected_path, self.linked_preview_text, self.linked_preview_image, self.linked_preview_tabs)

    def preview_selected_stats_file(self):
        sender_table = self.sender()
        if sender_table is None:
            return
        self._preview_from_table(sender_table, self.stats_preview_text, self.stats_preview_image, self.stats_preview_tabs)

    def preview_selected_trace_file(self):
        self._preview_from_table(self.trace_table, self.trace_preview_text, self.trace_preview_image, self.trace_preview_tabs)

    def preview_selected_report_file(self):
        self._preview_from_table(self.reports_only_table, self.reports_preview_text, self.reports_preview_image, self.reports_preview_tabs)

    def _preview_from_table(self, table_widget, text_widget, image_widget, tab_widget):
        row = table_widget.currentRow()
        if row < 0:
            return
        item = table_widget.item(row, 0)
        if not item:
            return
        full_path = item.data(Qt.UserRole)
        if not full_path:
            path_item = table_widget.item(row, 3)
            full_path = path_item.text() if path_item else ""
        if full_path:
            self._preview_file(full_path, text_widget, image_widget, tab_widget)

    def _find_related_files(self, student_id, student_name, source_image_path=""):
        search_roots = [os.path.join(os.getcwd(), "reports"), os.path.join(os.getcwd(), "read")]
        keywords = [k.strip() for k in [student_id, student_name] if k and k.strip()]
        if source_image_path:
            image_base = os.path.basename(source_image_path)
            image_stem = os.path.splitext(image_base)[0]
            keywords.extend([image_base, image_stem])
            for token in re.split(r"[_\-\s\.]+", image_stem):
                if token and len(token) >= 2:
                    keywords.append(token)
        if self.single_file_path:
            single_stem = os.path.splitext(os.path.basename(self.single_file_path))[0]
            keywords.append(single_stem)
        keywords = list(dict.fromkeys([k.lower() for k in keywords if k]))
        related_files = []
        all_files = []
        for root in search_roots:
            if not os.path.exists(root):
                continue
            for parent, _, files in os.walk(root):
                for file_name in files:
                    full_path = os.path.join(parent, file_name)
                    all_files.append(full_path)
                    name_lower = file_name.lower()
                    path_lower = full_path.lower()
                    matched = any(keyword in name_lower or keyword in path_lower for keyword in keywords)
                    if matched:
                        related_files.append(full_path)
        if not related_files and all_files:
            related_files = sorted(all_files, key=lambda p: os.path.getmtime(p), reverse=True)[:20]
        related_files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return related_files

    def _preview_file(self, file_path, text_widget, image_widget, tab_widget):
        if not os.path.exists(file_path):
            text_widget.setPlainText(f"文件不存在: {file_path}")
            image_widget.setText("暂无图片预览")
            tab_widget.setCurrentIndex(0)
            return
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
            pixmap = QPixmap(file_path)
            if pixmap.isNull():
                image_widget.setText(f"无法加载图片: {file_path}")
            else:
                scaled_pixmap = pixmap.scaled(image_widget.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                image_widget.setPixmap(scaled_pixmap)
            text_widget.setPlainText(file_path)
            tab_widget.setCurrentIndex(1)
            return
        try:
            with open(file_path, "r", encoding="utf-8") as file_obj:
                content = file_obj.read(20000)
            text_widget.setPlainText(content if content else "(空文件)")
        except UnicodeDecodeError:
            text_widget.setPlainText(f"该文件为二进制或非UTF-8文本: {file_path}")
        except Exception as exc:
            text_widget.setPlainText(f"读取失败: {exc}")
        image_widget.setPixmap(QPixmap())
        image_widget.setText("暂无图片预览")
        tab_widget.setCurrentIndex(0)

    def show_activation_dialog(self):
        """显示激活对话框"""
        dialog = ActivationDialog(self)
        dialog.activation_successful.connect(self.on_activation_successful)
        result = dialog.exec()

        # 如果用户取消激活，退出程序
        if result != QDialog.Accepted:
            sys.exit(0)

    def on_activation_successful(self):
        """激活成功后的回调"""
        self.initUI()
        self.apply_stylesheet()

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #F5F7FB;
                color: #1E293B;
                font-family: 'Segoe UI', 'Microsoft YaHei', Arial, sans-serif;
            }
            QGroupBox {
                font-weight: 600;
                font-size: 13px;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: #FFFFFF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px 0 6px;
                color: #3B82F6;
                font-weight: 600;
            }
            QLabel {
                color: #334155;
                font-size: 12px;
            }
            QCheckBox {
                color: #334155;
                font-size: 12px;
                spacing: 6px;
                padding: 2px 4px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #94A3B8;
                border-radius: 4px;
                background: #FFFFFF;
            }
            QCheckBox::indicator:checked {
                background: #2563EB;
                border-color: #2563EB;
            }
            QListWidget {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                padding: 4px;
                outline: none;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-radius: 6px;
                margin: 2px 0px;
            }
            QListWidget::item:selected {
                background-color: #DBEAFE;
                color: #1E40AF;
            }
            QTableWidget {
                gridline-color: #EEF2F7;
                background-color: #FFFFFF;
                alternate-background-color: #F8FAFC;
                selection-background-color: #DBEAFE;
                selection-color: #1E3A8A;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                font-size: 12px;
            }
            QHeaderView::section {
                background: #F8FAFC;
                padding: 8px 6px;
                border: 0px;
                border-bottom: 1px solid #E2E8F0;
                font-weight: 600;
                color: #475569;
                font-size: 12px;
            }
            QTableWidget QTableCornerButton::section {
                background: #F8FAFC;
                border: 0px;
                border-bottom: 1px solid #E2E8F0;
            }
            QProgressBar {
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                text-align: center;
                font-weight: 600;
                font-size: 11px;
                background-color: #F8FAFC;
                color: #475569;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3B82F6, stop:1 #2563EB);
                border-radius: 6px;
            }
            QTabWidget::pane {
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                background: #FFFFFF;
                top: -1px;
            }
            QTabBar::tab {
                background: #F8FAFC;
                color: #475569;
                border: 1px solid #E2E8F0;
                padding: 6px 10px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #FFFFFF;
                color: #1E40AF;
                border-bottom-color: #FFFFFF;
            }
            QPushButton {
                border: 1px solid #D9E2F0;
                border-radius: 8px;
            }
            QStatusBar {
                background: #FFFFFF;
                color: #64748B;
                border-top: 1px solid #E2E8F0;
                font-size: 12px;
            }
            QSplitter::handle {
                background-color: #EEF2F7;
                width: 2px;
            }
            QSplitter::handle:hover {
                background-color: #93C5FD;
            }
        """)

    def create_result_table(self):
        """创建结果表格"""
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels([
            "学号", "姓名", "客观题成绩", "主观题成绩", "总成绩"
        ])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        return table

    def clear_table(self):
        """清空表格数据"""
        self.result_table.clearContents()
        self.result_table.setRowCount(0)
        self.current_results.clear()

    def update_table(self, student):
        """更新表格数据"""
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)

        items = [
            student.student_id,
            student.name,
            str(student.objective_score),
            str(student.subjective_score),
            str(student.score)
        ]

        for col, text in enumerate(items):
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignCenter)
            if col == 0:
                item.setData(Qt.UserRole, getattr(student, "image_path", "") or "")
            self.result_table.setItem(row, col, item)

        self.current_results.append(student)
        
        # 自动滚动到最新行
        self.result_table.scrollToItem(self.result_table.item(row, 0))
        self.result_table.selectRow(row)
        self.refresh_linked_preview_for_selected_result()

    def load_answer_config(self):
        """加载TXT格式答案配置"""
        path, _ = QFileDialog.getOpenFileName(
            self, '选择答案文件',
            '', '文本文件 (*.txt)'
        )
        if not path:
            self.statusBar().showMessage("⚠️ 答案配置加载已取消", 3000)
            return

        try:
            self.answer_key = self.parse_answer_txt(path)
            self.system_config["answer_config_file"] = path  # 保存答案配置文件路径
            self.answer_config_loaded.emit(self.answer_key)
            self.statusBar().showMessage("✅ 答案配置加载成功", 3000)
            self.status_label.setText(f"已加载答案配置: {os.path.basename(path)}")
            self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        except Exception as e:
            self.statusBar().showMessage(f"❌ 配置解析失败：{str(e)}", 5000)
            self.status_label.setText("答案配置加载失败")
            self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")

    def parse_answer_txt(self, file_path: str) -> dict:
        """解析支持多选题的新答案配置文件格式"""
        from core.omr.question_parser import parse_multiple_choice_answers
        
        try:
            answers, scores, options = parse_multiple_choice_answers(file_path)
            
            answer_dict = {}
            for q_num, answer in answers.items():
                answer_dict[q_num] = {
                    'answer': answer,
                    'score': scores.get(q_num, 1.0),
                    'options': options.get(q_num, 4)
                }
                
            if not answer_dict:
                # 如果解析结果为空，可能是文件为空或格式全部不匹配
                # 这里不抛出异常，而是返回空字典，允许系统加载空配置
                print(f"警告: 配置文件 {file_path} 解析为空")
                
            return answer_dict
            
        except Exception as e:
            print(f"解析答案文件失败: {e}")
            raise ValueError(f"解析答案文件失败: {e}")

    # 添加应用系统配置的方法
    def apply_system_config(self, config):
        """应用系统配置"""
        self.system_config = config
        self.answer_key = config["objective_answer"]

        # 更新状态
        self.statusBar().showMessage("✅ 系统配置已更新", 3000)
        self.status_label.setText("系统配置已更新")
        self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")

        # 如果有客观题答案，发出信号
        if self.answer_key:
            self.answer_config_loaded.emit(self.answer_key)

    def load_single_file(self):
        """加载单个文件"""
        self.switch_main_page(0)
        self.clear_table()
        path, _ = QFileDialog.getOpenFileName(
            self, '选择答题卡', '',
            '图片文件 (*.jpg *.jpeg *.png)'
        )

        if path:
            self.single_file_path = path
            self.batch_folder_path = None  # 清除批量路径
            # 显示图片
            self.display_image(path)
            self.selected_source_label.setText(f"单文件: {path}")
            self.selected_items_list.clear()
            self.selected_items_list.addItem(path)
            self.status_label.setText(f"已选择文件: {os.path.basename(path)}")
            self.status_label.setStyleSheet("color: #3498db; font-weight: bold;")
            self.statusBar().showMessage(f"已选择文件: {path}", 3000)
        else:
            self.statusBar().showMessage("⚠️ 未选择任何文件，操作已取消", 3000)
            self.image_label.clear()
            self.image_label.setText('请选择图片或文件夹')
            self.status_label.setText("准备就绪")
            self.status_label.setStyleSheet("color: #7f8c8d;")

    def load_batch_folder(self):
        """加载批量处理文件夹"""
        self.switch_main_page(0)
        self.clear_table()
        folder = QFileDialog.getExistingDirectory(self, '选择批量处理文件夹')
        if folder:
            self.batch_folder_path = folder
            self.single_file_path = None  # 清除单个文件路径
            
            # 计算文件夹中的图片数量
            extensions = ('.jpg', '.jpeg', '.png')
            files = [f for f in os.listdir(folder) if f.lower().endswith(extensions)]
            self.total_files = len(files)
            
            self.image_label.clear()
            self.image_label.setText(f"已选择文件夹: {folder}\n\n包含 {self.total_files} 个图片文件")
            self.selected_source_label.setText(f"批量文件夹: {folder}")
            self.selected_items_list.clear()
            for file_name in sorted(files):
                self.selected_items_list.addItem(file_name)
            self.status_label.setText(f"已选择文件夹: {os.path.basename(folder)} ({self.total_files} 个图片)")
            self.status_label.setStyleSheet("color: #3498db; font-weight: bold;")
            self.statusBar().showMessage(f"已选择文件夹: {folder} (包含 {self.total_files} 个图片)", 3000)
            
            # 重置进度条
            self.progress_bar.setRange(0, self.total_files)
            self.progress_bar.setValue(0)
        else:
            self.statusBar().showMessage("⚠️ 文件夹选择已取消", 3000)
            self.status_label.setText("准备就绪")
            self.status_label.setStyleSheet("color: #7f8c8d;")

    def display_image(self, image_path):
        """显示图片到界面上"""
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            # 保持纵横比例缩放图片以适应标签大小
            label_size = self.image_label.size()
            scaled_pixmap = pixmap.scaled(
                label_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
        else:
            self.image_label.setText(f"无法加载图片: {image_path}")

    def process_single_file(self):
        """处理单个文件"""
        try:
            self.enable_objective = self.chk_objective.isChecked()
            self.enable_subjective = self.chk_subjective.isChecked()
            self.enable_student_info = self.chk_student_info.isChecked()
            self.enable_barcode = self.chk_barcode.isChecked()
            self.status_label.setText(f"正在处理: {os.path.basename(self.single_file_path)}")
            self.status_label.setStyleSheet("color: #e67e22; font-weight: bold;")
            QApplication.processEvents()  # 更新界面
            
            self.student_info = omr_processing(
                self.single_file_path,
                self.answer_key,
                self.system_config["api_key"],  # 传递API密钥
                subjective_answer_file=self.system_config.get("subjective_answer"),  # 传递主观题答案文件
                recognition_mode=self.recognition_mode,  # 传递识别模式
                enable_subjective=self.enable_subjective,  # 传递主观题开关
                enable_objective=self.enable_objective,  # 传递客观题开关
                enable_student_info=self.enable_student_info,  # 传递学生信息识别开关
                enable_barcode=self.enable_barcode,  # 传递条形码识别开关
                answer_config_file=self.system_config.get("answer_config_file"),  # 传递答案配置文件路径
                subjective_config=self.subjective_questions,  # 传递主观题配置
                gui_window=self  # 传递GUI窗口实例
            )
            self.update_table(self.student_info)
            
            self.status_label.setText(f"处理完成: {os.path.basename(self.single_file_path)}")
            self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            self.statusBar().showMessage("单个文件处理完成", 3000)
            self.refresh_statistics_view()
            
            # 更新进度条
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(1)
        except Exception as e:
            self.status_label.setText(f"处理失败: {str(e)}")
            self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
            self.statusBar().showMessage(f"处理失败：{str(e)}", 5000)

    def process_batch_files(self):
        """处理批量文件"""
        try:
            self.enable_objective = self.chk_objective.isChecked()
            self.enable_subjective = self.chk_subjective.isChecked()
            self.enable_student_info = self.chk_student_info.isChecked()
            self.enable_barcode = self.chk_barcode.isChecked()
            self.clear_table()
            extensions = ('.jpg', '.jpeg', '.png')
            files = [f for f in os.listdir(self.batch_folder_path)
                     if f.lower().endswith(extensions)]

            self.total_files = len(files)
            self.progress_bar.setRange(0, self.total_files)
            self.current_file_index = 0

            batch_results = []
            for filename in files:
                path = os.path.join(self.batch_folder_path, filename)

                # 更新状态和显示当前处理的图片
                self.status_label.setText(f"正在处理 ({self.current_file_index + 1}/{self.total_files}): {filename}")
                self.status_label.setStyleSheet("color: #e67e22; font-weight: bold;")
                self.display_image(path)
                
                # 设置进度条为当前文件的开始状态
                current_progress = (self.current_file_index * 100) // self.total_files
                self.progress_bar.setValue(current_progress)
                self.progress_bar.setFormat(f"📊 处理中 {self.current_file_index + 1}/{self.total_files} - {filename[:20]}...")
                QApplication.processEvents()  # 更新界面

                # 处理图片
                student = omr_processing(
                    path, 
                    self.answer_key,
                    config_manager.get_api_key(),  # 使用get_api_key()获取API密钥(包含试用期逻辑)
                    subjective_answer_file=self.system_config.get("subjective_answer"),  # 传递主观题答案文件
                    recognition_mode=self.recognition_mode,  # 传递识别模式
                    enable_subjective=self.enable_subjective,  # 传递主观题开关
                    enable_objective=self.enable_objective,  # 传递客观题开关
                    enable_student_info=self.enable_student_info,  # 传递学生信息识别开关
                    enable_barcode=self.enable_barcode,  # 传递条形码识别开关
                    answer_config_file=self.system_config.get("answer_config_file"),  # 传递答案配置文件路径
                    subjective_config=self.subjective_questions,  # 传递主观题配置
                    gui_window=self  # 传递GUI窗口实例
                )
                self.update_table(student)
                batch_results.append(student)

                # 处理完成后更新进度条
                self.current_file_index += 1
                final_progress = (self.current_file_index * 100) // self.total_files
                self.progress_bar.setValue(final_progress)
                self.progress_bar.setFormat(f"📊 已完成 {self.current_file_index}/{self.total_files} ({final_progress}%)")
                QApplication.processEvents()  # 更新界面

            self.status_label.setText(f"批量处理完成: {self.total_files} 个文件")
            self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            self.statusBar().showMessage(f"已处理 {self.total_files} 个文件", 5000)
            summary_path = self.save_batch_summary(batch_results)
            if summary_path:
                self.statusBar().showMessage(f"已生成批量汇总: {summary_path}", 5000)
            self.refresh_statistics_view()
        except Exception as e:
            self.status_label.setText(f"批量处理失败: {str(e)}")
            self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
            self.statusBar().showMessage(f"批量处理失败：{str(e)}", 5000)
            print(f"Error Details:\n{traceback.format_exc()}")  # 打印完整错误日志

    def save_batch_summary(self, students):
        if not students:
            return None
        output_dir = os.path.join(os.getcwd(), "read")
        os.makedirs(output_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"batch_summary_{timestamp}.csv")
        data = []
        question_numbers = set()
        for student in students:
            if hasattr(student, "question_scores") and student.question_scores:
                question_numbers.update(student.question_scores.keys())
        sorted_questions = sorted(question_numbers)
        for student in students:
            image_name = os.path.basename(getattr(student, "image_path", "") or "")
            row = {
                "学号": student.student_id or "",
                "姓名": student.name or "",
                "客观题成绩": f"{getattr(student, 'objective_score', 0):.2f}",
                "主观题成绩": f"{getattr(student, 'subjective_score', 0):.2f}",
                "总成绩": f"{getattr(student, 'score', 0):.2f}",
                "错题数": len(getattr(student, "wrong_questions", []) or []),
                "空白数": len(getattr(student, "blank_questions", []) or []),
                "原图文件": image_name
            }
            for q_num in sorted_questions:
                score_val = 0.0
                if hasattr(student, "question_scores") and student.question_scores:
                    score_val = student.question_scores.get(q_num, 0.0)
                row[f"Q{q_num}得分"] = f"{score_val:.2f}"
            data.append(row)
        df = pd.DataFrame(data)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        return output_path

    def start_processing(self):
        """识别按钮点击后的处理入口"""
        # 输入验证检查
        error_msg = []

        # 检查答案配置
        if not self.answer_key:
            error_msg.append("答案配置未加载")

        # 检查文件选择
        file_selected = False
        if self.single_file_path:
            if not os.path.isfile(self.single_file_path):
                error_msg.append("单个文件路径无效")
            else:
                file_selected = True
        elif self.batch_folder_path:
            if not os.path.isdir(self.batch_folder_path):
                error_msg.append("文件夹路径无效")
            else:
                file_selected = True
        else:
            error_msg.append("未选择任何文件或文件夹")

        if error_msg:
            error_text = "❌ 无法开始识别：\n" + "\n".join(error_msg)
            self.statusBar().showMessage(error_text, 5000)
            self.status_label.setText("识别失败: " + ", ".join(error_msg))
            self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
            return

        try:
            # 更新处理状态
            self.btn_recognition.setEnabled(False)  # 禁用识别按钮
            self.btn_recognition.setText("处理中...")
            self.statusBar().showMessage("⏳ 正在识别，请稍候...")
            QApplication.processEvents()  # 强制刷新界面

            # 执行处理流程
            if self.single_file_path:
                self.process_single_file()
            elif self.batch_folder_path:
                self.process_batch_files()

            # 处理完成提示
            self.statusBar().showMessage("✅ 识别处理完成", 3000)

        except Exception as e:
            self.statusBar().showMessage(f"❌ 处理过程中发生错误：{str(e)}", 8000)
            self.status_label.setText(f"处理错误: {str(e)}")
            self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
            print(f"Error Details:\n{traceback.format_exc()}")  # 打印完整错误日志

        finally:
            # 恢复界面状态
            self.btn_recognition.setEnabled(True)
            self.btn_recognition.setText("开始识别")
            QApplication.processEvents()  # 确保界面状态更新

    def auto_load_config(self):
        """启动时自动加载配置"""
        try:
            if config_manager.is_auto_load_enabled():
                # 自动加载客观题答案
                objective_path = config_manager.get_objective_answer_path()
                if objective_path and os.path.exists(objective_path):
                    try:
                        self.answer_key = self.parse_answer_txt(objective_path)
                        self.system_config["objective_answer"] = self.answer_key
                        self.system_config["answer_config_file"] = objective_path  # 保存答案配置文件路径
                        self.status_label.setText(f"已自动加载客观题答案: {os.path.basename(objective_path)}")
                        self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
                    except Exception as e:
                        print(f"自动加载客观题答案失败: {e}")
                
                # 自动加载主观题答案
                subjective_path = config_manager.get_subjective_answer_path()
                if subjective_path and os.path.exists(subjective_path):
                    self.system_config["subjective_answer"] = subjective_path
                
                # 自动加载API密钥
                api_key = config_manager.get_api_key()
                self.system_config["api_key"] = api_key
                self.system_config["api_base_url"] = config_manager.get("api_base_url", "https://api.siliconflow.cn/v1")
                self.system_config["model_name"] = config_manager.get("model_name", "Qwen/Qwen3-VL-30B-A3B-Instruct")
                self.system_config["available_models"] = config_manager.get("available_models", [])

                if self.system_config_panel is not None:
                    self.system_config_panel.refresh_from_config(self.system_config)
                
                # 自动加载学生信息识别开关状态
                self.enable_student_info = config_manager.is_student_info_enabled()
                self.enable_barcode = config_manager.get("enable_barcode", False)
                self.chk_student_info.setChecked(self.enable_student_info)
                self.chk_barcode.setChecked(self.enable_barcode)
                self.chk_objective.setChecked(self.enable_objective)
                self.chk_subjective.setChecked(self.enable_subjective)

                # 自动加载识别模式（A/B）；不再更新主界面按钮，识别模式仅在系统配置中设定
                try:
                    self.recognition_mode = config_manager.get_recognition_mode()
                except Exception:
                    self.recognition_mode = "A"
                
                # 更新状态显示
                status = config_manager.get_status()
                if status["objective_answer_exists"] and status["api_key_configured"]:
                    self.statusBar().showMessage("✅ 配置已自动加载完成", 3000)
                elif status["objective_answer_exists"]:
                    self.statusBar().showMessage("⚠️ 客观题答案已加载，但API密钥未配置", 5000)
                else:
                    self.statusBar().showMessage("⚠️ 请配置系统设置", 3000)
            else:
                self.statusBar().showMessage("ℹ️ 自动加载已禁用，请手动配置", 3000)
        except Exception as e:
            print(f"自动加载配置失败: {e}")
            self.statusBar().showMessage("⚠️ 配置加载失败，请手动配置", 3000)

    def open_system_config(self):
        """打开系统配置对话框"""
        if hasattr(self, "system_config_panel") and self.system_config_panel is not None:
            self.system_config_panel.show()
        self.switch_main_page(4)

    def on_config_saved(self, config):
        """配置保存后的回调"""
        try:
            # 更新系统配置
            self.system_config.update(config)
            
            # 更新客观题答案
            if config.get("objective_answer"):
                self.answer_key = config["objective_answer"]
            
            # 同步答案配置文件路径，确保后续 omr_processing 使用一致的路径
            if config.get("answer_config_file"):
                self.system_config["answer_config_file"] = config["answer_config_file"]
            
            # 保存到配置管理器
            config_updates = {}
            
            # 保存客观题答案路径（如果有的话）
            if hasattr(self, '_last_objective_path'):
                config_updates["objective_answer_path"] = "config\\answer_config\\objective_answer.txt"
                # 同步到系统配置，保持界面和处理流程一致
                self.system_config["answer_config_file"] = self._last_objective_path
            
            # 保存API密钥
            if "api_key" in config:
                config_updates["api_key"] = config["api_key"]
            
            # 保存API基础URL
            if config.get("api_base_url"):
                config_updates["api_base_url"] = config["api_base_url"]
            
            # 保存模型名称
            if config.get("model_name"):
                config_updates["model_name"] = config["model_name"]

            # 保存模型列表
            if config.get("available_models"):
                config_updates["available_models"] = config["available_models"]
                self.system_config["available_models"] = config["available_models"]

            if config.get("objective_scoring_rule"):
                config_updates["objective_scoring_rule"] = config["objective_scoring_rule"]
            
            # 保存学生信息识别开关状态
            config_updates["enable_student_info"] = self.enable_student_info
            config_updates["enable_barcode"] = self.enable_barcode

            # 保存识别模式/题列布局（若对话框返回该字段）
            rec_updates = {}
            if config.get("recognition_mode"):
                rec_updates["mode"] = config["recognition_mode"]
                # 同步内存值（主界面不再显示按钮）
                self.recognition_mode = config["recognition_mode"].upper()
            if config.get("recognition_layout"):
                rec_updates["layout"] = config["recognition_layout"]
            if config.get("recognition_group_size") is not None:
                try:
                    rec_updates["group_size"] = int(config["recognition_group_size"])
                except Exception:
                    pass
            
            # 保存检测置信度阈值
            if config.get("recognition_conf_thres") is not None:
                try:
                    rec_updates["conf_thres"] = float(config["recognition_conf_thres"])
                except Exception:
                    pass

            if rec_updates:
                config_updates["recognition"] = rec_updates
            
            # 批量更新配置
            if config_updates:
                config_manager.update(config_updates)

            # 配置更新后同步刷新智能助手客户端，避免继续使用旧API参数
            if self.smart_agent_dialog and getattr(self.smart_agent_dialog, "agent", None):
                self.smart_agent_dialog.agent.update_config()
            
            # 更新状态显示
            self.status_label.setText("系统配置已更新")
            self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            self.statusBar().showMessage("✅ 系统配置保存成功", 3000)
            
        except Exception as e:
            self.status_label.setText(f"配置保存失败: {str(e)}")
            self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
            self.statusBar().showMessage(f"❌ 配置保存失败：{str(e)}", 5000)

    # 已移除：toggle_recognition_mode（识别模式不再由主界面切换）

    def toggle_subjective_grading(self, state):
        self.enable_subjective = state == Qt.Checked
        if self.enable_subjective:
            self.statusBar().showMessage("✅ 主观题评分已开启", 2000)
        else:
            self.statusBar().showMessage("⚠️ 主观题评分已关闭", 2000)
        self.update_switch_status_labels()
    
    def toggle_objective_grading(self, state):
        self.enable_objective = state == Qt.Checked
        if self.enable_objective:
            self.statusBar().showMessage("✅ 客观题阅卷已开启", 2000)
        else:
            self.statusBar().showMessage("⚠️ 客观题阅卷已关闭", 2000)
        self.update_switch_status_labels()

    def toggle_student_info_recognition(self, state):
        self.enable_student_info = state == Qt.Checked
        if self.enable_student_info:
            self.statusBar().showMessage("✅ 学生信息识别已开启", 2000)
        else:
            self.statusBar().showMessage("⚠️ 学生信息识别已关闭", 2000)
        self.update_switch_status_labels()

    def toggle_barcode_recognition(self, state):
        self.enable_barcode = state == Qt.Checked
        if self.enable_barcode:
            self.statusBar().showMessage("✅ 条形码识别已开启", 2000)
        else:
            self.statusBar().showMessage("⚠️ 条形码识别已关闭", 2000)
        self.update_switch_status_labels()

    def export_data(self):
        """导出表格数据"""
        if self.result_table.rowCount() == 0:
            self.statusBar().showMessage("⚠️ 没有可导出的数据", 3000)
            self.status_label.setText("导出失败: 没有可导出的数据")
            self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
            return

        data = []
        for row in range(self.result_table.rowCount()):
            row_data = {
                "学号": self.result_table.item(row, 0).text(),
                "姓名": self.result_table.item(row, 1).text(),
                "客观题成绩": self.result_table.item(row, 2).text(),
                "主观题成绩": self.result_table.item(row, 3).text(),
                "总成绩": self.result_table.item(row, 4).text()
            }
            data.append(row_data)

        df = pd.DataFrame(data)
        path, _ = QFileDialog.getSaveFileName(
            self, "保存成绩单",
            "成绩单.xlsx",
            "Excel文件 (*.xlsx);;CSV文件 (*.csv)"
        )

        if path:
            try:
                self.status_label.setText("正在导出数据...")
                self.status_label.setStyleSheet("color: #e67e22; font-weight: bold;")
                QApplication.processEvents()  # 更新界面
                
                if path.endswith('.csv'):
                    df.to_csv(path, index=False)
                else:
                    if not path.endswith('.xlsx'):
                        path += '.xlsx'
                    df.to_excel(path, index=False)
                
                self.status_label.setText(f"导出成功: {os.path.basename(path)}")
                self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
                self.statusBar().showMessage(f"✅ 成功导出到：{path}", 5000)
            except Exception as e:
                self.status_label.setText(f"导出失败: {str(e)}")
                self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                self.statusBar().showMessage(f"❌ 导出失败：{str(e)}", 5000)


    def open_smart_agent(self):
        """打开智能助手对话框"""
        if not self.assistant_panel.isVisible():
            self.toggle_assistant_panel()
        self.switch_main_page(0)
        self.assistant_state_label.setText("右侧助手已启用")

    def _to_objective_questions(self, answer_dict):
        """将解析后的答案字典转换为界面表格使用的数据结构"""
        objective_questions = {}
        for q_num, q_data in sorted(answer_dict.items()):
            answer = q_data.get("answer")
            score = q_data.get("score", 1.0)
            if isinstance(score, float):
                score = round(score, 2)

            objective_questions[q_num] = {
                "type": "单选题" if isinstance(answer, str) else "多选题",
                "score": score,
                "answer": answer,
                "options": q_data.get("options", 4),
            }
        return objective_questions

    def _reload_objective_config_views(self):
        """重新读取客观题配置文件并刷新主界面/配置面板"""
        objective_path = config_manager.get_objective_answer_path()
        if not objective_path or not os.path.exists(objective_path):
            return False

        answer_dict = self.parse_answer_txt(objective_path)
        self.answer_key = answer_dict
        self.system_config["objective_answer"] = answer_dict
        self.system_config["answer_config_file"] = objective_path
        self.answer_config_loaded.emit(answer_dict)

        if self.system_config_panel is not None:
            if hasattr(self.system_config_panel, "current_config"):
                self.system_config_panel.current_config["objective_answer"] = answer_dict
                self.system_config_panel.current_config["objective_answer_file"] = objective_path
            self.system_config_panel.objective_questions = self._to_objective_questions(answer_dict)
            self.system_config_panel.update_questions_table()

        return True

    # on_smart_agent_closed 方法可以删除或保留但不再使用
    def on_smart_agent_closed(self):
        """智能助手关闭回调"""
        # 不再销毁实例
        pass

    def on_smart_agent_config_applied(self, config_type):
        """智能助手配置应用后的回调"""
        self.auto_load_config()
        if config_type == 'objective':
            try:
                self._reload_objective_config_views()
            except Exception as e:
                print(f"刷新客观题配置界面失败: {e}")
            self.statusBar().showMessage("✅ 客观题配置已通过智能助手更新", 3000)
        elif config_type == 'subjective':
            self.statusBar().showMessage("✅ 主观题配置已通过智能助手更新", 3000)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = OMRGUI()
    ex.show()
    sys.exit(app.exec())
