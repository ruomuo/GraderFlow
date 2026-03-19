from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QLineEdit, QMessageBox, QApplication,
                             QProgressBar)
from PySide6.QtCore import Qt, Signal, QTimer
from utils.activation import ActivationManager, HardwareInfo

class ActivationDialog(QDialog):
    activation_successful = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("软件激活")
        self.setMinimumSize(500, 300)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.activation_manager = ActivationManager()
        self.is_trial_mode = False
        self.initUI()
        self.check_status()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # 标题
        title_label = QLabel("智能答题卡批改系统 - 激活")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; margin-bottom: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 试用信息显示区 (默认隐藏，根据状态显示)
        self.trial_info_label = QLabel("")
        self.trial_info_label.setAlignment(Qt.AlignCenter)
        self.trial_info_label.setStyleSheet("font-size: 14px; color: #e67e22; font-weight: bold;")
        layout.addWidget(self.trial_info_label)

        # 激活码输入
        input_group = QVBoxLayout()
        input_label = QLabel("激活码:")
        input_label.setStyleSheet("font-weight: bold;")
        self.activation_input = QLineEdit()
        self.activation_input.setPlaceholderText("请输入您的激活码")
        self.activation_input.setMinimumWidth(300)
        self.activation_input.setMinimumHeight(35)
        
        input_group.addWidget(input_label)
        input_group.addWidget(self.activation_input)
        layout.addLayout(input_group)

        # 硬件ID显示
        hw_layout = QHBoxLayout()
        self.hw_id_label = QLabel("硬件ID:")
        self.hw_id_value = QLabel(HardwareInfo.get_hardware_id())
        self.hw_id_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.hw_id_value.setStyleSheet("background-color: #f5f5f5; padding: 8px; border-radius: 4px; border: 1px solid #ddd;")
        
        copy_btn = QPushButton("复制")
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.clicked.connect(self.copy_machine_code)
        
        hw_layout.addWidget(self.hw_id_label)
        hw_layout.addWidget(self.hw_id_value, 1)
        hw_layout.addWidget(copy_btn)
        layout.addLayout(hw_layout)

        # 状态信息
        self.status_label = QLabel("请输入激活码进行激活")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #7f8c8d; margin-top: 5px;")
        layout.addWidget(self.status_label)

        # 进度条（默认隐藏）
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # 不确定进度
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        layout.addStretch()

        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 试用按钮 (继续试用)
        self.trial_btn = QPushButton("继续试用")
        self.trial_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        self.trial_btn.clicked.connect(self.on_trial)
        self.trial_btn.setVisible(False) # 默认隐藏
        
        # 激活按钮
        self.activate_button = QPushButton("立即激活")
        self.activate_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1c6ea4;
            }
        """)
        self.activate_button.clicked.connect(self.verify_activation)

        # 退出/取消按钮
        self.cancel_button = QPushButton("退出")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.trial_btn)
        button_layout.addStretch(1)
        button_layout.addWidget(self.activate_button)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)
        
    def check_status(self):
        """检查当前的试用状态"""
        # 检查试用期
        can_trial, msg, days = self.activation_manager.check_trial_status()
        
        if can_trial:
            self.trial_info_label.setText(f"{msg} (支持全功能试用)")
            self.trial_btn.setVisible(True)
            self.trial_btn.setText(f"继续试用 ({days}天)")
            self.is_trial_mode = True
        else:
            self.trial_info_label.setText(msg)
            self.trial_info_label.setStyleSheet("color: red; font-size: 14px; font-weight: bold;")
            self.trial_btn.setVisible(False)
            self.is_trial_mode = False
            self.status_label.setText("试用期已结束或无效，请激活")
            self.status_label.setStyleSheet("color: red;")

    def copy_machine_code(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(HardwareInfo.get_hardware_id())
        QMessageBox.information(self, "提示", "硬件ID已复制到剪贴板")

    def on_trial(self):
        """点击继续试用"""
        can_trial, msg, _ = self.activation_manager.check_trial_status()
        if can_trial:
            self.activation_successful.emit()
            self.accept()
        else:
            QMessageBox.warning(self, "提示", msg)
            self.check_status()

    def verify_activation(self):
        """验证激活码"""
        activation_code = self.activation_input.text().strip()
        if not activation_code:
            QMessageBox.warning(self, "验证失败", "请输入激活码")
            return

        # 显示进度条
        self.progress_bar.setVisible(True)
        self.status_label.setText("正在连接服务器验证激活码...")
        self.status_label.setStyleSheet("color: #3498db;")
        self.activate_button.setEnabled(False)
        self.trial_btn.setEnabled(False)
        self.cancel_button.setEnabled(False)
        QApplication.processEvents()

        # 使用定时器模拟网络请求延迟(避免界面卡死)
        QTimer.singleShot(100, lambda: self._perform_activation(activation_code))

    def _perform_activation(self, activation_code):
        """执行激活过程"""
        try:
            success, message = self.activation_manager.activate(activation_code)

            # 隐藏进度条
            self.progress_bar.setVisible(False)

            if success:
                self.status_label.setText(message)
                self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
                QMessageBox.information(self, "激活成功", message)
                self.activation_successful.emit()
                self.accept()
            else:
                self.status_label.setText(message)
                self.status_label.setStyleSheet("color: #e74c3c;")
                QMessageBox.warning(self, "激活失败", message)
        except Exception as e:
            self.status_label.setText(f"激活过程中出错: {str(e)}")
            self.status_label.setStyleSheet("color: #e74c3c;")
            QMessageBox.critical(self, "激活错误", f"激活过程中出错: {str(e)}")
        finally:
            self.activate_button.setEnabled(True)
            self.trial_btn.setEnabled(self.is_trial_mode)
            self.cancel_button.setEnabled(True)
