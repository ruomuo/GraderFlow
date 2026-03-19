import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QPushButton, QFileDialog,
                               QTableWidget, QTableWidgetItem, QHeaderView, 
                               QProgressBar, QSplitter, QFrame, QGridLayout,
                               QGroupBox, QDialog, QTabWidget, QLineEdit, QFormLayout,
                               QTextEdit, QMessageBox, QComboBox, QSpinBox, 
                               QDoubleSpinBox, QListWidget, QCheckBox)
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
            answer_dict = self.parent().parse_answer_txt(path)
            
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
            'subjective_answers.txt', '文本文件 (*.txt)'
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
    
    def load_current_config(self):
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
        
        if self.current_config.get("api_base_url"):
            self.api_base_url_input.setText(self.current_config["api_base_url"])
        
        if self.current_config.get("model_name"):
            # 设置模型选择
            index = self.model_combo.findText(self.current_config["model_name"])
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
        
        # 加载客观题配置（从配置文件重新读取）
        try:
            # 使用实例的配置管理器获取最新的配置文件路径
            objective_path = self.config_manager.get_objective_answer_path()
            
            print(f"尝试加载客观题配置文件: {objective_path}")
            
            if os.path.exists(objective_path):
                # 重新解析配置文件
                from core.omr.question_parser import parse_multiple_choice_answers
                answers, scores, options = parse_multiple_choice_answers(objective_path)
                
                print(f"成功解析配置文件，找到 {len(answers)} 道题目")
                
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
            answer_dict = self.parent().parse_answer_txt(path)
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
                objective_path = get_config_file_path('answer_multiple.txt')
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
                    'objective_answer_path': 'answer_config\\answer_multiple.txt'
                })
                
                # 更新当前配置：保存的文件路径与解析后的客观题答案字典
                self.current_config['objective_answer_file'] = objective_path
                try:
                    # 解析刚保存的文件，确保传入评分流程的是最新一致的字典结构
                    self.current_config['objective_answer'] = self.parent().parse_answer_txt(objective_path)
                    # 同步答案文件路径，供主窗口传递给 omr_processor 使用
                    self.current_config['answer_config_file'] = objective_path
                except Exception as e:
                    print(f"解析保存后的客观题配置失败: {e}")
            
            # 保存主观题配置
            if self.subjective_questions:
                subjective_path = get_config_file_path('test_subjective_answer.txt')
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
                    'subjective_answer_path': 'answer_config\\test_subjective_answer.txt'
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
            self.accept()
            
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
            "api_key": "",  # 默认API密钥
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

        # 创建主窗口部件
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        self.setCentralWidget(main_widget)

        # 顶部标题
        title_label = QLabel('🎯 智能答题卡批改系统')
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont('Microsoft YaHei', 20, QFont.Bold))
        title_label.setStyleSheet("""
            color: #2C3E50; 
            margin-bottom: 15px;
            padding: 15px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #4A90E2, stop:0.5 #50C878, stop:1 #4A90E2);
            border-radius: 10px;
            font-weight: 700;
        """)
        main_layout.addWidget(title_label)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        main_layout.addWidget(splitter, 1)

        # 左侧图像显示区域
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # 图像显示框
        image_group = QGroupBox("答题卡预览")
        image_layout = QVBoxLayout(image_group)
        
        self.image_label = QLabel('📷 请选择图片或文件夹')
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(500, 400)
        self.image_label.setStyleSheet("""
            border: 2px dashed #4A90E2; 
            border-radius: 10px; 
            background-color: #F8F9FA; 
            padding: 20px;
            color: #6C757D;
            font-size: 16px;
            font-weight: 500;
        """)
        image_layout.addWidget(self.image_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("📊 %v/%m (%p%)")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #E1E8ED; 
                border-radius: 8px; 
                text-align: center;
                font-weight: 600;
                font-size: 13px;
                background-color: #F8F9FA;
                color: #495057;
                min-height: 25px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4A90E2, stop:1 #50C878);
                border-radius: 6px;
            }
        """)
        image_layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel('✨ 准备就绪')
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            color: #6C757D; 
            margin-top: 10px;
            font-size: 14px;
            font-weight: 500;
            padding: 5px;
        """)
        image_layout.addWidget(self.status_label)
        
        left_layout.addWidget(image_group)
        
        # 右侧控制面板
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 操作按钮组
        control_group = QGroupBox("操作面板")
        control_layout = QGridLayout(control_group)
        
        # 现代简约风格按钮样式
        primary_button_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4A90E2, stop:1 #3A7BC8);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-weight: 600;
                font-size: 14px;
                min-height: 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5BA0F2, stop:1 #4A90E2);
            }
            QPushButton:pressed {
                background: #3A7BC8;
            }
            QPushButton:disabled {
                background-color: #BDC3C7;
                color: #7F8C8D;
            }
        """
        
        secondary_button_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #50C878, stop:1 #45B369);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-weight: 600;
                font-size: 14px;
                min-height: 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #60D888, stop:1 #50C878);
            }
            QPushButton:pressed {
                background: #45B369;
            }
        """
        
        accent_button_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FF6B6B, stop:1 #E55A5A);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-weight: 600;
                font-size: 14px;
                min-height: 20px;
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
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFB347, stop:1 #E6A23C);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-weight: 600;
                font-size: 14px;
                min-height: 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFC357, stop:1 #FFB347);
            }
            QPushButton:pressed {
                background: #E6A23C;
            }
        """
        
        toggle_off_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #95A5A6, stop:1 #7F8C8D);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-weight: 600;
                font-size: 14px;
                min-height: 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #A5B5B6, stop:1 #95A5A6);
            }
            QPushButton:pressed {
                background: #7F8C8D;
            }
        """
        
        self.btn_file = QPushButton('📁 选择单个文件')
        self.btn_file.setStyleSheet(primary_button_style)
        
        self.btn_batch = QPushButton('📂 选择批量处理文件夹')
        self.btn_batch.setStyleSheet(primary_button_style)
        
        self.btn_answer = QPushButton('⚙️ 系统配置')
        self.btn_answer.setStyleSheet(primary_button_style)
        
        self.btn_smart_agent = QPushButton('🤖 智能助手')
        self.btn_smart_agent.setStyleSheet(primary_button_style)
        
        # 已移除：A/B模式切换按钮（识别模式仅在系统配置中设定）
        
        # 主观题评分开关按钮
        self.btn_subjective_toggle = QPushButton('✅ 主观题: 开启')
        self.btn_subjective_toggle.setStyleSheet(secondary_button_style)
        self.btn_subjective_toggle.setToolTip('点击切换主观题评分开关\n开启: 启用主观题评分\n关闭: 仅评分客观题')
        
        # 客观题阅卷开关按钮
        self.btn_objective_toggle = QPushButton('✅ 客观题: 开启')
        self.btn_objective_toggle.setStyleSheet(secondary_button_style)
        self.btn_objective_toggle.setToolTip('点击切换客观题阅卷开关\n开启: 启用客观题阅卷\n关闭: 仅评分主观题')
        
        # 学生信息识别开关按钮
        self.btn_student_info_toggle = QPushButton('✅ 学生信息: 开启')
        self.btn_student_info_toggle.setStyleSheet(secondary_button_style)
        self.btn_student_info_toggle.setToolTip('点击切换学生信息识别开关\n开启: 启用学生信息识别\n关闭: 跳过学生信息识别')
        
        self.btn_recognition = QPushButton('🚀 开始识别')
        self.btn_recognition.setStyleSheet(secondary_button_style)
        
        self.btn_export = QPushButton('📊 导出成绩')
        self.btn_export.setStyleSheet(warning_button_style)
        
        # 保存样式供切换时使用
        self.primary_style = primary_button_style
        self.secondary_style = secondary_button_style
        self.accent_style = accent_button_style
        self.warning_style = warning_button_style
        self.toggle_off_style = toggle_off_style
        
        control_layout.addWidget(self.btn_file, 0, 0)
        control_layout.addWidget(self.btn_batch, 0, 1)
        control_layout.addWidget(self.btn_answer, 1, 0)
        control_layout.addWidget(self.btn_smart_agent, 1, 1)
        
        # 开关按钮（识别模式按钮已移除，改由系统配置设定）
        control_layout.addWidget(self.btn_objective_toggle, 3, 0)
        control_layout.addWidget(self.btn_subjective_toggle, 3, 1)
        control_layout.addWidget(self.btn_student_info_toggle, 4, 0, 1, 2)
        
        control_layout.addWidget(self.btn_recognition, 5, 0, 1, 2)
        control_layout.addWidget(self.btn_export, 6, 0, 1, 2)
        
        right_layout.addWidget(control_group)

        # 结果表格
        table_group = QGroupBox("识别结果")
        table_layout = QVBoxLayout(table_group)
        
        self.result_table = self.create_result_table()
        table_layout.addWidget(self.result_table)
        
        right_layout.addWidget(table_group, 1)  # 表格占据更多空间

        # 添加到分割器
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([int(self.width() * 0.6), int(self.width() * 0.4)])

        # 底部状态栏
        self.statusBar().setStyleSheet("background-color: #f5f5f5; color: #2c3e50;")

        # 连接信号
        self.btn_file.clicked.connect(self.load_single_file)
        self.btn_batch.clicked.connect(self.load_batch_folder)
        self.btn_answer.clicked.connect(self.open_system_config)
        self.btn_smart_agent.clicked.connect(self.open_smart_agent)
        self.btn_subjective_toggle.clicked.connect(self.toggle_subjective_grading)
        self.btn_objective_toggle.clicked.connect(self.toggle_objective_grading)
        self.btn_student_info_toggle.clicked.connect(self.toggle_student_info_recognition)
        self.btn_recognition.clicked.connect(self.start_processing)
        self.btn_export.clicked.connect(self.export_data)

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
        # 现代简约风格全局样式
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #FAFBFC;
                color: #2C3E50;
                font-family: 'Segoe UI', 'Microsoft YaHei', Arial, sans-serif;
            }
            QGroupBox {
                font-weight: 600;
                font-size: 14px;
                border: 2px solid #E1E8ED;
                border-radius: 10px;
                margin-top: 15px;
                padding-top: 15px;
                background-color: #FFFFFF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #4A90E2;
                font-weight: 700;
            }
            QLabel {
                color: #2C3E50;
                font-size: 13px;
            }
            QTableWidget {
                gridline-color: #E1E8ED;
                background-color: #FFFFFF;
                alternate-background-color: #F8F9FA;
                selection-background-color: #4A90E2;
                selection-color: white;
                border: 1px solid #E1E8ED;
                border-radius: 8px;
                font-size: 13px;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F8F9FA, stop:1 #E9ECEF);
                padding: 8px;
                border: 1px solid #E1E8ED;
                font-weight: 600;
                color: #495057;
                font-size: 13px;
            }
            QTableWidget QTableCornerButton::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F8F9FA, stop:1 #E9ECEF);
                border: 1px solid #E1E8ED;
            }
            QProgressBar {
                border: 2px solid #E1E8ED;
                border-radius: 8px;
                text-align: center;
                font-weight: 600;
                font-size: 13px;
                background-color: #F8F9FA;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4A90E2, stop:1 #50C878);
                border-radius: 6px;
            }
            QStatusBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFFFFF, stop:1 #F8F9FA);
                color: #495057;
                border-top: 1px solid #E1E8ED;
                font-size: 13px;
            }
            QSplitter::handle {
                background-color: #E1E8ED;
                width: 2px;
            }
            QSplitter::handle:hover {
                background-color: #4A90E2;
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
            self.result_table.setItem(row, col, item)

        self.current_results.append(student)
        
        # 自动滚动到最新行
        self.result_table.scrollToItem(self.result_table.item(row, 0))

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

    # 添加系统配置对话框打开方法
    def open_system_config(self):
        """打开系统配置对话框"""
        dialog = SystemConfigDialog(self, self.system_config)
        dialog.config_saved.connect(self.apply_system_config)
        dialog.exec()

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
                answer_config_file=self.system_config.get("answer_config_file"),  # 传递答案配置文件路径
                subjective_config=self.subjective_questions,  # 传递主观题配置
                gui_window=self  # 传递GUI窗口实例
            )
            self.update_table(self.student_info)
            
            self.status_label.setText(f"处理完成: {os.path.basename(self.single_file_path)}")
            self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            self.statusBar().showMessage("单个文件处理完成", 3000)
            
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
                if api_key:
                    self.system_config["api_key"] = api_key
                
                # 自动加载学生信息识别开关状态
                self.enable_student_info = config_manager.is_student_info_enabled()
                # 更新按钮状态
                if self.enable_student_info:
                    self.btn_student_info_toggle.setText("✅ 学生信息: 开启")
                    self.btn_student_info_toggle.setStyleSheet(self.secondary_style)
                else:
                    self.btn_student_info_toggle.setText("❌ 学生信息: 关闭")
                    self.btn_student_info_toggle.setStyleSheet(self.toggle_off_style)

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
        # 准备当前配置数据
        current_config = {
            "objective_answer": self.system_config.get("objective_answer", {}),
            "subjective_answer": self.system_config.get("subjective_answer", ""),
            # 获取原始配置的API Key，不使用get_api_key()以避免显示内置试用Key
            "api_key": config_manager.get("api_key", ""),
            "api_base_url": config_manager.get("api_base_url", "https://api.siliconflow.cn/v1"),
            "model_name": config_manager.get("model_name", "Qwen/Qwen3-VL-30B-A3B-Instruct"),
            "available_models": config_manager.get("available_models", [
                "zai-org/GLM-4.6V",
                "Qwen/Qwen3-VL-8B-Instruct",
                "Qwen/Qwen3-VL-8B-Thinking",
                "Qwen/Qwen3-VL-32B-Instruct",
                "Qwen/Qwen3-VL-32B-Thinking",
                "Qwen/Qwen3-VL-30B-A3B-Instruct",
                "Qwen/Qwen3-VL-30B-A3B-Thinking",
                "Qwen/Qwen3-VL-235B-A22B-Instruct",
                "Qwen/Qwen3-VL-235B-A22B-Thinking"
            ])
        }
        # 带入当前识别模式
        current_config["recognition_mode"] = config_manager.get_recognition_mode()
        
        # 如果当前配置为空，尝试从配置管理器加载
        if not current_config["objective_answer"]:
            objective_path = config_manager.get_objective_answer_path()
            if objective_path and os.path.exists(objective_path):
                try:
                    current_config["objective_answer"] = self.parse_answer_txt(objective_path)
                except Exception as e:
                    print(f"加载客观题答案失败: {e}")
        
        if not current_config["subjective_answer"]:
            current_config["subjective_answer"] = config_manager.get_subjective_answer_path()
        
        # 打开配置对话框
        dialog = SystemConfigDialog(self, current_config)
        dialog.config_saved.connect(self.on_config_saved)
        dialog.exec()

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
                config_updates["objective_answer_path"] = self._last_objective_path
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
            
            # 更新状态显示
            self.status_label.setText("系统配置已更新")
            self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            self.statusBar().showMessage("✅ 系统配置保存成功", 3000)
            
        except Exception as e:
            self.status_label.setText(f"配置保存失败: {str(e)}")
            self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
            self.statusBar().showMessage(f"❌ 配置保存失败：{str(e)}", 5000)

    # 已移除：toggle_recognition_mode（识别模式不再由主界面切换）

    def toggle_subjective_grading(self):
        """切换主观题评分开关"""
        self.enable_subjective = not self.enable_subjective
        if self.enable_subjective:
            self.btn_subjective_toggle.setText("✅ 主观题: 开启")
            self.btn_subjective_toggle.setStyleSheet(self.secondary_style)
            self.statusBar().showMessage("✅ 主观题评分已开启", 2000)
        else:
            self.btn_subjective_toggle.setText("❌ 主观题: 关闭")
            self.btn_subjective_toggle.setStyleSheet(self.toggle_off_style)
            self.statusBar().showMessage("⚠️ 主观题评分已关闭", 2000)
    
    def toggle_objective_grading(self):
        """切换客观题阅卷开关"""
        self.enable_objective = not self.enable_objective
        if self.enable_objective:
            self.btn_objective_toggle.setText("✅ 客观题: 开启")
            self.btn_objective_toggle.setStyleSheet(self.secondary_style)
            self.statusBar().showMessage("✅ 客观题阅卷已开启", 2000)
        else:
            self.btn_objective_toggle.setText("❌ 客观题: 关闭")
            self.btn_objective_toggle.setStyleSheet(self.toggle_off_style)
            self.statusBar().showMessage("⚠️ 客观题阅卷已关闭", 2000)

    def toggle_student_info_recognition(self):
        """切换学生信息识别开关"""
        self.enable_student_info = not self.enable_student_info
        if self.enable_student_info:
            self.btn_student_info_toggle.setText("✅ 学生信息: 开启")
            self.btn_student_info_toggle.setStyleSheet(self.secondary_style)
            self.statusBar().showMessage("✅ 学生信息识别已开启", 2000)
        else:
            self.btn_student_info_toggle.setText("❌ 学生信息: 关闭")
            self.btn_student_info_toggle.setStyleSheet(self.toggle_off_style)
            self.statusBar().showMessage("⚠️ 学生信息识别已关闭", 2000)

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
        if self.smart_agent_dialog is None:
            self.smart_agent_dialog = SmartAgentDialog(self)
            self.smart_agent_dialog.config_applied.connect(self.on_smart_agent_config_applied)
            # 不再连接 finished 信号来销毁实例，而是保持实例以保存上下文
        
        self.smart_agent_dialog.show()
        self.smart_agent_dialog.raise_()
        self.smart_agent_dialog.activateWindow()

    # on_smart_agent_closed 方法可以删除或保留但不再使用
    def on_smart_agent_closed(self):
        """智能助手关闭回调"""
        # 不再销毁实例
        pass

    def on_smart_agent_config_applied(self, config_type):
        """智能助手配置应用后的回调"""
        self.auto_load_config()
        if config_type == 'objective':
            self.statusBar().showMessage("✅ 客观题配置已通过智能助手更新", 3000)
        elif config_type == 'subjective':
            self.statusBar().showMessage("✅ 主观题配置已通过智能助手更新", 3000)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = OMRGUI()
    ex.show()
    sys.exit(app.exec())
