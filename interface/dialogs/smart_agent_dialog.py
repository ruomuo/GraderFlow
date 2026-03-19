import re
import os
import tempfile
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, 
                               QLineEdit, QPushButton, QLabel, QSplitter, 
                               QWidget, QMessageBox, QProgressBar, QFileDialog)
from PySide6.QtCore import Qt, Signal, QThread, QMimeData, QDateTime
from PySide6.QtGui import QFont, QTextCursor, QPixmap, QKeyEvent, QImage
from core.llm_agent import LLMAgent
from utils.config_manager import config_manager
import os

class ChatInputTextEdit(QTextEdit):
    """支持回车发送的输入框，支持粘贴图片"""
    submit_signal = Signal()
    image_pasted = Signal(str)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if event.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier):
                # Ctrl+Enter 或 Shift+Enter 换行
                super().keyPressEvent(event)
            else:
                # Enter 发送
                self.submit_signal.emit()
                event.accept()
        else:
            super().keyPressEvent(event)

    def canInsertFromMimeData(self, source):
        if source.hasImage():
            return True
        return super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source):
        if source.hasImage():
            image = source.imageData()
            if image:
                if isinstance(image, QPixmap):
                    image = image.toImage()
                
                if isinstance(image, QImage):
                    # Generate temp filename
                    timestamp = QDateTime.currentDateTime().toString("yyyyMMdd_HHmmss_zzz")
                    temp_dir = tempfile.gettempdir()
                    file_path = os.path.join(temp_dir, f"paste_{timestamp}.png")
                    image.save(file_path, "PNG")
                    self.image_pasted.emit(file_path)
                    return
        super().insertFromMimeData(source)

class ChatThread(QThread):
    """后台聊天线程"""
    token_received = Signal(str)
    finished_signal = Signal()
    
    def __init__(self, agent, message, image_path=None):
        super().__init__()
        self.agent = agent
        self.message = message
        self.image_path = image_path
        
    def run(self):
        for token in self.agent.chat(self.message, self.image_path):
            self.token_received.emit(token)
        self.finished_signal.emit()

class SmartAgentDialog(QDialog):
    """智能助手对话框"""
    config_applied = Signal(str)  # 信号：配置已应用 (type: 'objective' or 'subjective')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("智能阅卷助手")
        self.resize(900, 700)
        self.setWindowFlags(Qt.Window)  # 独立窗口
        
        # 如果父窗口已经有了agent实例，应该复用它（但这里为了简化，我们假设main_window保持了dialog实例）
        # 如果是从main_window传入的，agent已经在self.agent中（如果这里不重新创建）
        # 由于main_window.py中是 persistent dialog，所以__init__只调一次，self.agent会保持
        self.agent = LLMAgent()
        self.current_objective_config = None
        self.current_subjective_config = None
        self.selected_image_path = None
        
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 顶部提示
        header = QLabel("💡 与AI对话以自动配置答案。支持上传试卷图片识别。\n例如：“请帮我识别图片中的客观题配置”")
        header.setStyleSheet("color: #666; font-style: italic; margin-bottom: 5px;")
        layout.addWidget(header)
        
        # 聊天记录显示区
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("""
            QTextEdit {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                padding: 15px;
                font-family: "Microsoft YaHei";
                font-size: 14px;
            }
        """)
        layout.addWidget(self.chat_history, 1)
        
        # 操作按钮区域 (默认隐藏，检测到配置时显示)
        self.action_area = QWidget()
        action_layout = QHBoxLayout(self.action_area)
        action_layout.setContentsMargins(0, 0, 0, 0)
        
        self.btn_apply_obj = QPushButton("应用客观题配置")
        self.btn_apply_obj.setStyleSheet("""
            QPushButton {
                background-color: #3498db; color: white; border-radius: 4px; padding: 6px 15px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.btn_apply_obj.clicked.connect(self.apply_objective_config)
        self.btn_apply_obj.hide()
        
        self.btn_apply_subj = QPushButton("应用主观题配置")
        self.btn_apply_subj.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71; color: white; border-radius: 4px; padding: 6px 15px; font-weight: bold;
            }
            QPushButton:hover { background-color: #27ae60; }
        """)
        self.btn_apply_subj.clicked.connect(self.apply_subjective_config)
        self.btn_apply_subj.hide()
        
        action_layout.addWidget(self.btn_apply_obj)
        action_layout.addWidget(self.btn_apply_subj)
        action_layout.addStretch()
        layout.addWidget(self.action_area)
        
        # 图片预览区
        self.image_preview_area = QWidget()
        preview_layout = QHBoxLayout(self.image_preview_area)
        preview_layout.setContentsMargins(0, 5, 0, 5)
        
        self.lbl_image_preview = QLabel()
        self.lbl_image_preview.setFixedSize(100, 100)
        self.lbl_image_preview.setScaledContents(True)
        self.lbl_image_preview.setStyleSheet("border: 1px dashed #aaa; background: #eee; border-radius: 4px;")
        
        self.btn_clear_image = QPushButton("×")
        self.btn_clear_image.setFixedSize(20, 20)
        self.btn_clear_image.setCursor(Qt.PointingHandCursor)
        self.btn_clear_image.setStyleSheet("border-radius: 10px; background: #e74c3c; color: white; font-weight: bold; border: none;")
        self.btn_clear_image.clicked.connect(self.clear_image)
        
        preview_layout.addWidget(self.lbl_image_preview)
        preview_layout.addWidget(self.btn_clear_image, 0, Qt.AlignTop)
        preview_layout.addStretch()
        
        self.image_preview_area.hide()
        layout.addWidget(self.image_preview_area)
        
        # 输入区
        input_container = QWidget()
        input_container.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #DDD;
                border-radius: 8px;
            }
        """)
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(10, 10, 10, 10)
        
        # 图片上传按钮
        self.btn_upload = QPushButton("📷")
        self.btn_upload.setToolTip("上传试卷图片")
        self.btn_upload.setFixedSize(36, 36)
        self.btn_upload.setCursor(Qt.PointingHandCursor)
        self.btn_upload.setStyleSheet("""
            QPushButton {
                background-color: #f1f2f6;
                color: #57606f;
                border-radius: 18px;
                font-size: 18px;
                border: none;
            }
            QPushButton:hover {
                background-color: #dfe4ea;
            }
        """)
        self.btn_upload.clicked.connect(self.upload_image)
        input_layout.addWidget(self.btn_upload)

        # 自定义输入框
        self.input_box = ChatInputTextEdit()
        self.input_box.setMaximumHeight(80)
        self.input_box.setPlaceholderText("在此输入您的需求... (Enter发送，Ctrl+Enter换行，支持Ctrl+V粘贴图片)")
        self.input_box.setStyleSheet("border: none; background: transparent;")
        self.input_box.submit_signal.connect(self.send_message)
        self.input_box.image_pasted.connect(self.handle_pasted_image)
        
        self.btn_send = QPushButton("发送")
        self.btn_send.setFixedSize(70, 36)
        self.btn_send.setCursor(Qt.PointingHandCursor)
        self.btn_send.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                font-weight: bold;
                border-radius: 18px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.btn_send.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.input_box, 1)
        input_layout.addWidget(self.btn_send)
        
        layout.addWidget(input_container)

    def upload_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择试卷图片", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.selected_image_path = file_path
            pixmap = QPixmap(file_path)
            self.lbl_image_preview.setPixmap(pixmap)
            self.image_preview_area.show()

    def handle_pasted_image(self, file_path):
        """处理粘贴的图片"""
        self.selected_image_path = file_path
        pixmap = QPixmap(file_path)
        self.lbl_image_preview.setPixmap(pixmap)
        self.image_preview_area.show()

    def clear_image(self):
        self.selected_image_path = None
        self.image_preview_area.hide()

    def send_message(self):
        msg = self.input_box.toPlainText().strip()
        if not msg and not self.selected_image_path:
            return
            
        # 显示用户消息
        user_msg = msg
        if self.selected_image_path:
            user_msg += f"<br><span style='color:gray; font-size:12px;'>[已上传图片: {os.path.basename(self.selected_image_path)}]</span>"
        
        self.append_user_bubble(user_msg)
        
        # 清空输入状态
        self.input_box.clear()
        self.btn_send.setEnabled(False)
        image_path = self.selected_image_path
        self.clear_image()  # 发送后清除图片选择
        
        # 开始后台请求
        self.thread = ChatThread(self.agent, msg, image_path)
        self.thread.token_received.connect(self.on_token_received)
        self.thread.finished_signal.connect(self.on_chat_finished)
        
        # 准备接收助手消息 (创建AI气泡)
        self.current_response = ""
        self.append_ai_bubble_start()
        self.thread.start()

    def append_user_bubble(self, text):
        """添加用户消息气泡（右侧）"""
        html = f"""
        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 10px;">
            <tr>
                <td>&nbsp;</td>
                <td align="right" valign="top">
                    <div style="
                        background-color: #95EC69; 
                        color: black; 
                        padding: 10px 14px; 
                        border-radius: 12px; 
                        border-top-right-radius: 2px;
                        display: inline-block;
                        text-align: left;
                    ">
                        {text.replace(chr(10), '<br>')}
                    </div>
                </td>
                <td width="10"></td>
            </tr>
        </table>
        """
        self.append_html(html)

    def append_ai_bubble_start(self):
        """添加AI消息气泡开始（左侧）"""
        # 我们插入一个带有唯一ID或标记的表格，以便后续更新？
        # QTextEdit 追加模式下，我们只需插入表格头，然后光标会停在后面。
        # 为了流式输出，我们先插入一个容器，然后尝试定位到里面。
        # 实际上，QTextEdit 插入HTML后，光标通常在插入块之后。
        # 简单策略：先插入 "AI正在思考..." 的占位符，或者直接开始流式输出。
        # 为了美观，我们使用一个Table，左侧是AI头像(可选)，右侧是内容。
        
        # 技巧：使用 insertHtml 插入一个开放的 div 并不容易，因为 HTML 会自动闭合。
        # 替代方案：每次 token 更新都重写整个 bubble？太慢。
        # 妥协方案：流式输出时只显示纯文本或简单格式，完成后再用 Bubble 包装替换？
        # 或者：流式输出时，不带 Bubble 样式，或者带一个简单的左侧引用样式。
        
        # 让我们尝试：插入一个 Table，光标定位到 Cell 中？
        # 这在 QTextEdit 中很难控制。
        
        # 回退策略：流式输出时不显示气泡背景，只显示 "🤖 AI: " 前缀。
        # 完成后，删除这段文本，替换为漂亮的 Bubble HTML。
        
        cursor = self.chat_history.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.response_start_pos = cursor.position()
        
        # 插入临时头部
        cursor.insertHtml("<br><div style='color: #2980b9; font-weight: bold;'>🤖 AI Thinking...</div>")
        self.chat_history.setTextCursor(cursor)
        self.chat_history.ensureCursorVisible()

    def append_html(self, html):
        cursor = self.chat_history.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml(html)
        self.chat_history.setTextCursor(cursor)
        self.chat_history.ensureCursorVisible()

    def on_token_received(self, token):
        self.current_response += token
        
        # 实时更新（简单追加文本，不带样式，避免HTML破坏）
        # 我们删除之前的 "AI Thinking..." 或之前的 token 内容，重新插入？
        # 不，直接追加最快。但在 "Thinking" 后面追加不太好看。
        
        # 改进：第一次收到 token 时，替换 "Thinking..."
        cursor = self.chat_history.textCursor()
        cursor.setPosition(self.response_start_pos)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        
        # 简单处理：直接显示当前累积的文本（Markdown未渲染）
        # 为了避免闪烁，只在长文本时才全量替换？或者只追加 token？
        # 追加 token 无法处理 Markdown（如加粗需要闭合标签）。
        # 所以通常做法是：清空当前段落 -> 渲染 Markdown -> 插入 HTML。
        
        # 渲染当前 Markdown
        html_content = self.format_markdown(self.current_response)
        
        # 这里用一个简易的 AI Bubble 包装
        bubble_html = f"""
        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 10px;">
            <tr>
                <td width="10"></td>
                <td align="left" valign="top">
                    <div style="
                        background-color: white; 
                        color: black; 
                        padding: 10px 14px; 
                        border-radius: 12px; 
                        border-top-left-radius: 2px;
                        border: 1px solid #E0E0E0;
                        display: inline-block;
                    ">
                        {html_content}
                    </div>
                </td>
                <td>&nbsp;</td>
            </tr>
        </table>
        """
        
        # 替换从 response_start_pos 到结尾的内容
        cursor.insertHtml(bubble_html)
        self.chat_history.ensureCursorVisible()
        
        # 注意：每次 insertHtml 都会改变 position。
        # 我们需要保持 response_start_pos 不变，但其实 insertHtml 后原来的 range 被替换了。
        # 下一次 update 时，我们需要重新选中从 response_start_pos 开始的所有内容。
        # 这里的 response_start_pos 指的是文档中的绝对位置。
        # 只要我们不删除 response_start_pos 之前的字符，它应该保持有效？
        # 不一定，insertHtml 可能会合并 block。
        
        # 修正策略：
        # 使用一个固定的 anchor 或者是每次清空最后一块。
        # 由于每次重绘整个 Bubble 会导致滚动条跳动和性能问题（如果文本很长）。
        # 但对于短对话是可以接受的。
        
    def on_chat_finished(self):
        self.btn_send.setEnabled(True)
        # 聊天结束，解析代码块
        self.parse_configs(self.current_response)
        
        # 最后一次确保格式正确
        cursor = self.chat_history.textCursor()
        cursor.setPosition(self.response_start_pos)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        
        html_content = self.format_markdown(self.current_response)
        bubble_html = f"""
        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 10px;">
            <tr>
                <td width="10"></td>
                <td align="left" valign="top">
                    <div style="
                        background-color: white; 
                        color: black; 
                        padding: 10px 14px; 
                        border-radius: 12px; 
                        border-top-left-radius: 2px;
                        border: 1px solid #E0E0E0;
                        display: inline-block;
                    ">
                        {html_content}
                    </div>
                </td>
                <td>&nbsp;</td>
            </tr>
        </table>
        """
        cursor.insertHtml(bubble_html)
        self.chat_history.ensureCursorVisible()

    def format_markdown(self, text):
        """简单的Markdown转HTML"""
        import html as html_lib
        # 先进行 HTML 转义，防止原始内容干扰 HTML 结构
        text = html_lib.escape(text)
        
        # 换行转 <br>
        text = text.replace("\n", "<br>")
        
        # 粗体 **text** -> <b>text</b>
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        
        # 代码块处理 (恢复被转义的换行)
        # 这是一个简化的处理，对于复杂的嵌套代码块可能不够完美
        def replace_code_block(match):
            content = match.group(1)
            # 恢复代码块内的原始内容（去掉br）
            content = content.replace("<br>", "\n")
            # 简单的样式
            return f'<div style="background:#f8f9fa; padding:10px; border:1px solid #ddd; border-radius:4px; font-family:Consolas,monospace; margin:5px 0;"><pre style="margin:0;">{content}</pre></div>'
            
        # 我们之前已经 escape 了，所以 ``` 会变成 ``` (如果 escape 没有转义反引号的话，通常不转义)
        # 但 html.escape 不转义 `
        
        # 针对 objective 和 subjective 特殊块
        def replace_objective_block(match):
            content = match.group(1).replace("<br>", "\n")
            return f'<div style="background:#e8f6f3; padding:10px; border-left:4px solid #2ecc71; margin:5px 0;"><div style="color:#27ae60; font-weight:bold; font-size:12px; margin-bottom:5px;">客观题配置</div><pre style="margin:0;">{content}</pre></div>'

        def replace_subjective_block(match):
            content = match.group(1).replace("<br>", "\n")
            return f'<div style="background:#fcf3cf; padding:10px; border-left:4px solid #f1c40f; margin:5px 0;"><div style="color:#f39c12; font-weight:bold; font-size:12px; margin-bottom:5px;">主观题配置</div><pre style="margin:0;">{content}</pre></div>'

        text = re.sub(r'```objective(.*?)```', replace_objective_block, text, flags=re.DOTALL)
        text = re.sub(r'```subjective(.*?)```', replace_subjective_block, text, flags=re.DOTALL)
                      
        # 通用代码块
        text = re.sub(r'```(.*?)```', replace_code_block, text, flags=re.DOTALL)
        
        return text

    def parse_configs(self, text):
        """解析回复中的配置块"""
        # 注意：这里解析的是原始文本，不是 HTML
        # 使用 findall 捕获所有 objective 块
        obj_matches = re.findall(r'```objective\s*(.*?)```', text, re.DOTALL)
        
        # 使用 findall 捕获所有 subjective 块
        subj_matches = re.findall(r'```subjective\s*(.*?)```', text, re.DOTALL)
        
        if obj_matches:
            # 合并所有块的内容
            self.current_objective_config = "\n".join([m.strip() for m in obj_matches])
            self.btn_apply_obj.show()
            # 统计行数作为题目数
            count = len([l for l in self.current_objective_config.splitlines() if l.strip() and not l.strip().startswith('#')])
            self.btn_apply_obj.setText(f"应用客观题配置 ({count}题)")
        else:
            self.btn_apply_obj.hide()
            self.current_objective_config = None
            
        if subj_matches:
            # 合并所有块的内容，中间加换行
            self.current_subjective_config = "\n\n".join([m.strip() for m in subj_matches])
            self.btn_apply_subj.show()
            self.btn_apply_subj.setText("应用主观题配置")
        else:
            self.btn_apply_subj.hide()
            self.current_subjective_config = None

    def apply_objective_config(self):
        if not self.current_objective_config:
            return
            
        try:
            path = config_manager.get_objective_answer_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            valid_lines = []
            for line in self.current_objective_config.splitlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                parts = line.split(':')
                if len(parts) >= 2 and parts[0].strip().isdigit():
                    # 规范化数据格式，确保包含分值和选项数
                    # 格式：题号:答案:分值:选项个数
                    q_num = parts[0].strip()
                    answer = parts[1].strip()
                    
                    # 默认值
                    score = "2.0"  # 默认2分
                    options = "4"  # 默认4个选项
                    
                    if len(parts) >= 3 and parts[2].strip():
                        score = parts[2].strip()
                    
                    if len(parts) >= 4 and parts[3].strip():
                        options = parts[3].strip()
                        
                    # 重构行数据
                    valid_lines.append(f"{q_num}:{answer}:{score}:{options}")
            
            if not valid_lines:
                QMessageBox.warning(self, "警告", "生成的配置中没有有效的题目数据，无法应用。请重试或手动复制。")
                return
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write("# 客观题答案配置文件 (AI自动生成)\n")
                f.write("# 格式：题号:答案:分值:选项个数\n\n")
                f.write('\n'.join(valid_lines))
            
            QMessageBox.information(self, "成功", "客观题配置已保存！")
            self.config_applied.emit('objective')
            self.btn_apply_obj.hide()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")

    def apply_subjective_config(self):
        if not self.current_subjective_config:
            return
            
        try:
            path = config_manager.get_subjective_answer_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write("# 主观题答案配置文件 (AI自动生成)\n\n")
                f.write(self.current_subjective_config)
            
            QMessageBox.information(self, "成功", "主观题配置已保存！")
            self.config_applied.emit('subjective')
            self.btn_apply_subj.hide()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")

