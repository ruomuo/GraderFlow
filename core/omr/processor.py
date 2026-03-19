from core.data.student import StudentInfo
from core.omr.detector import predict
from core.omr.recognizer import recognize_answer_main, deskew_image
from utils.config_manager import config_manager
from core.omr.info_recognizer import recognize_name
from pathlib import Path
import shutil
import os
import time
import cv2
import numpy as np
from core.subjective.llm_api import get_info_json
from core.subjective.grader import grade_subjective_questions_direct, generate_subjective_report_direct
from core.omr.annotator import annotate_answer_sheet, copy_original_to_read, create_summary_image, save_grading_records
from core.omr.question_parser import parse_question_types


def show_progress(message, step=None, total_steps=None, gui_window=None):
    """
    显示处理进度信息
    
    参数:
        message: 进度消息
        step: 当前步骤（可选）
        total_steps: 总步骤数（可选）
        gui_window: GUI窗口实例（可选）
    """
    timestamp = time.strftime("%H:%M:%S")
    
    # 在终端显示进度（保留原有功能）
    if step is not None and total_steps is not None:
        progress_bar = "█" * (step * 20 // total_steps) + "░" * (20 - step * 20 // total_steps)
        print(f"[{timestamp}] 🔄 [{progress_bar}] ({step}/{total_steps}) {message}")
    else:
        print(f"[{timestamp}] 🔄 {message}")
    
    # 在GUI界面显示进度
    if gui_window is not None:
        try:
            # 更新状态栏消息
            gui_window.statusBar().showMessage(f"🔄 {message}")
            
            # 更新状态标签
            if hasattr(gui_window, 'status_label'):
                gui_window.status_label.setText(message)
                gui_window.status_label.setStyleSheet("color: #2196F3; font-weight: bold;")
            
            # 更新进度条（如果提供了步骤信息）
            if step is not None and total_steps is not None and hasattr(gui_window, 'progress_bar'):
                progress_percentage = int((step / total_steps) * 100)
                gui_window.progress_bar.setValue(progress_percentage)
                gui_window.progress_bar.setFormat(f"📊 {step}/{total_steps} ({progress_percentage}%)")
            
            # 强制刷新界面
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()
            
        except Exception as e:
            # 如果GUI更新失败，只在终端显示错误，不影响主流程
            print(f"GUI更新失败: {e}")


def clean_detect_dir():
    """清理 runs/detect 目录下的所有内容"""
    detect_dir = Path("runs/detect")

    try:
        # 递归删除目录及其所有内容
        if detect_dir.exists():
            shutil.rmtree(detect_dir)
            print(f"✅ 成功清理目录: {detect_dir}")

        # 重新创建空目录
        os.makedirs(detect_dir, exist_ok=True)

    except Exception as e:
        print(f"❌ 清理失败: {str(e)}")
        raise


def prepare_image_file(image_path: str) -> Path:
    """
    准备图片文件，复制到指定目录
    
    参数:
        image_path: 原始图片路径
        
    返回:
        Path: 处理后的图片路径
    """
    save_dir = Path("undet_img")
    target_path = save_dir / "sheet.jpg"

    # 强制创建目录（忽略已存在情况）
    save_dir.mkdir(parents=True, exist_ok=True)

    # 清空目录下所有文件
    for f in save_dir.glob('*'):
        if f.is_file():
            f.unlink()

    # 保存当前文件（始终命名为sheet.jpg）
    shutil.copy(image_path, target_path)
    return target_path


def process_objective_questions(student: StudentInfo, answer_key: dict, question_types: dict = None, recognition_mode: str = "B", question_types_file: str = None, original_image_path: str = None, answer_config_file: str = None, gui_window=None) -> None:
    """
    处理客观题识别和评分
    
    参数:
        student: 学生信息对象
        answer_key: 客观题答案配置
        question_types: 题目类型配置（可选）
        recognition_mode: 识别模式，"A"为自然顺序，"B"为列优先顺序
        question_types_file: 题目类型配置文件路径（可选）
        original_image_path: 原始图片路径（用于标注）
        answer_config_file: 答案配置文件路径（可选，用于获取选项数量配置）
    """
    try:
        show_progress("正在检测答题框位置...", 1, 4, gui_window)
        
        # 调用预测函数
        show_progress("正在识别客观题答案...", 2, 4, gui_window)
        predict()
        
        # 识别答题内容
        show_progress("正在处理识别结果...", 3, 4, gui_window)
        # 从系统配置读取题列布局（默认为 row）
        try:
            recognition_layout = config_manager.get_recognition_config().get("layout", "row")
        except Exception:
            recognition_layout = "row"
        # 读取题组数量（每图题数），默认为 5
        try:
            recognition_group_size = config_manager.get_recognition_group_size()
        except Exception:
            recognition_group_size = 5

        recognition_results, detailed_results = recognize_answer_main(
            mode=recognition_mode,
            question_types_file=question_types_file,
            answer_config_file=answer_config_file,
            layout=recognition_layout,
            group_size=recognition_group_size,
        )
        
        # 将识别结果添加到学生答案中
        print(f"🔍 客观题识别结果调试:")
        print(f"📊 识别结果类型: {type(recognition_results)}")
        print(f"📊 识别结果内容: {recognition_results}")
        
        # recognition_results是一个字典，键为文件名，值为该文件的识别结果字典
        if recognition_results:
            # 合并所有文件的识别结果
            for filename, file_results in recognition_results.items():
                print(f"📄 处理文件: {filename}")
                print(f"📄 文件结果: {file_results}")
                for question_num, answer in file_results.items():
                    student.answers[question_num] = answer
                    print(f"  题目 {question_num}: {answer}")
            
            # 合并详细结果
            if detailed_results:
                # 直接保存详细结果结构 {filename: {q_num: details}} 以供annotator使用
                student.detailed_answers = detailed_results
                # 同时也为了调试打印一下结构
                print(f"📊 详细结果结构已保存: {list(detailed_results.keys())}")
            else:
                print("⚠️ 警告: 没有详细识别结果")
        
        # 计算客观题得分（统一使用StudentInfo.calculate_score以填充错题与空白题）
        if answer_key:
            print(f"🔍 客观题评分调试:")
            print(f"📚 答案配置数量: {len(answer_key)}")
            print(f"📚 答案配置类型: {type(answer_key)}")
            print(f"📚 答案配置内容: {answer_key}")

            # 重置统计字段，防止残留影响展示
            student.wrong_questions = []
            student.blank_questions = []
            student.question_scores = {}

            try:
                try:
                    scoring_rule = config_manager.get_objective_scoring_rule()
                except Exception:
                    scoring_rule = "standard"
                total_score = student.calculate_score(answer_key, question_types, scoring_rule)
                print(f"🎯 客观题评分结果: {student.objective_score:.1f} 分，合计总分: {total_score:.1f}")
            except Exception as e:
                student.add_recognition_log(f"客观题计分异常: {str(e)}")
                print(f"客观题计分异常: {str(e)}")

            show_progress("正在计算客观题得分...", 4, 4, gui_window)
            
        # 生成标注图片
        print(f"DEBUG: 准备生成标注图片. 原始路径: {original_image_path}, 是否存在: {os.path.exists(original_image_path) if original_image_path else 'None'}")
        if original_image_path and os.path.exists(original_image_path):
            try:
                show_progress("正在生成标注图片...", gui_window=gui_window)
                # 标注答题卡图片（显示错题和总分）
                annotated_path = annotate_answer_sheet(original_image_path, student)
                print(f"DEBUG: annotate_answer_sheet 返回: {annotated_path}")
                if annotated_path:
                    student.add_recognition_log(f"标注图片已生成: {annotated_path}")
                else:
                    print("DEBUG: annotate_answer_sheet 返回 None")
                
                # 复制原始图片到read文件夹作为备份
                original_copy_path = copy_original_to_read(original_image_path, student)
                if original_copy_path:
                    student.add_recognition_log(f"原始图片已备份: {original_copy_path}")
                
                # 创建评分摘要图片
                summary_path = create_summary_image(student)
                if summary_path:
                    student.add_recognition_log(f"评分摘要已生成: {summary_path}")
                
                # 保存客观题阅卷记录到CSV
                records_path = save_grading_records(student)
                if records_path:
                    student.add_recognition_log(f"阅卷记录已保存: {records_path}")
                    
            except Exception as e:
                student.add_recognition_log(f"图片标注过程出错: {str(e)}")
        else:
            student.add_recognition_log("未提供原始图片路径，跳过图片标注")
            
    except Exception as e:
        student.add_recognition_log(f"客观题处理异常: {str(e)}")
        raise


def process_student_info(student: StudentInfo, image_path: str, api_key: str, gui_window=None) -> None:
    """
    处理学生信息识别（姓名和学号）
    
    参数:
        student: 学生信息对象
        image_path: 图片路径
        api_key: API密钥
        gui_window: GUI窗口实例（可选）
    """
    try:
        print(f"🔍 学生信息识别调试:")
        print(f"📷 图片路径: {image_path}")
        show_progress("正在提取试卷姓名及准考证号（请求多模态大模型，时间较久）...", gui_window=gui_window)
        
        info_result = get_info_json(api_key, image_path)
        print(f"📊 API返回结果: {info_result}")
        print(f"📊 结果类型: {type(info_result)}")
        
        if info_result and len(info_result) == 2:
            stu_name, stu_number = info_result
            
            # 保存识别到的信息（即使只有姓名或学号）
            if stu_name:
                student.name = stu_name
            if stu_number:
                student.student_id = stu_number
            
            if stu_name and stu_number:
                # 完全识别成功
                print(f"✅ 学生信息识别成功: {student.name} ({student.student_id})")
                show_progress(f"成功识别学生信息: {student.name} ({student.student_id})", gui_window=gui_window)
                student.add_recognition_log(f"学生信息识别成功: {student.name} ({student.student_id})")
            elif stu_name or stu_number:
                # 部分识别成功
                name_display = stu_name if stu_name else "未识别"
                number_display = stu_number if stu_number else "未识别"
                print(f"⚠️ 学生信息部分识别:")
                print(f"  - 姓名: {name_display}")
                print(f"  - 学号: {number_display}")
                show_progress(f"部分识别学生信息: {name_display} ({number_display})", gui_window=gui_window)
                student.add_recognition_log(f"部分识别学生信息: {name_display} ({number_display})")
            else:
                # 完全识别失败
                print(f"❌ 学生信息识别失败:")
                print(f"  - 姓名: 未识别")
                print(f"  - 学号: 未识别")
                show_progress("姓名和学号均未识别，将使用默认名称", gui_window=gui_window)
                student.add_recognition_log("姓名和学号均未识别，将使用默认名称")
        else:
            print(f"❌ 学生信息识别失败: API返回格式异常")
            show_progress("姓名或学号识别失败，将使用默认名称", gui_window=gui_window)
            student.add_recognition_log("姓名或学号识别失败，将使用默认名称")
            
    except Exception as e:
        print(f"❌ 学生信息识别异常: {str(e)}")
        show_progress("学生信息识别异常，将使用默认名称", gui_window=gui_window)
        student.add_recognition_log(f"学生信息识别异常: {str(e)}")
        student.has_name_id = False


def process_subjective_questions(student: StudentInfo, subjective_answer_file: str, api_key: str, subjective_config: dict = None, gui_window=None, image_path: str = None) -> None:
    """
    处理主观题阅卷
    
    参数:
        student: 学生信息对象
        subjective_answer_file: 主观题答案文件路径
        gui_window: GUI窗口实例（可选）
        image_path: 图片路径（可选，通常为纠偏后的图片路径）
    """
    if not subjective_answer_file or not os.path.exists(subjective_answer_file):
        show_progress("主观题答案文件不存在，跳过主观题阅卷", gui_window=gui_window)
        student.add_recognition_log("主观题答案文件不存在，跳过主观题阅卷")
        return
    
    try:
        show_progress("正在读取配置答案...", gui_window=gui_window)
        with open(subjective_answer_file, 'r', encoding='utf-8') as f:
            answer_content = f.read().strip()
        
        show_progress(f"答案文件读取完成，内容长度: {len(answer_content)} 字符", gui_window=gui_window)
        
        if not answer_content:
            show_progress("主观题答案文件为空，跳过主观题阅卷", gui_window=gui_window)
            student.add_recognition_log("主观题答案文件为空，跳过主观题阅卷")
            return
        
        show_progress("正在请求多模态大模型进行主观题阅卷（时间较久，请耐心等待）...", gui_window=gui_window)
        
        # 更新GUI进度条显示主观题评分状态
        if gui_window is not None:
            try:
                if hasattr(gui_window, 'progress_bar'):
                    gui_window.progress_bar.setFormat("🤖 主观题评分中，请耐心等待...")
                    from PySide6.QtWidgets import QApplication
                    QApplication.processEvents()
            except Exception as e:
                print(f"GUI进度条更新失败: {e}")
        
        # 提取用户提示词
        user_prompts = {}
        if subjective_config:
            for q_num, q_data in subjective_config.items():
                if isinstance(q_data, dict) and 'user_prompt' in q_data:
                    prompt = q_data['user_prompt'].strip()
                    if prompt:
                        user_prompts[q_num] = prompt
        
        # 调用主观题阅卷函数
        target_image_path = image_path if image_path else student.image_path
        grading_result = grade_subjective_questions_direct(
            target_image_path,
            answer_content,
            api_key,  # 使用传入的API密钥
            user_prompts=user_prompts  # 传递用户提示词
        )
        
        if grading_result:
            show_progress("主观题阅卷完成，正在处理结果...", gui_window=gui_window)
            
            # 添加调试信息
            print("🔍 主观题评分结果调试:")
            print(f"grading_result 类型: {type(grading_result)}")
            print(f"grading_result 内容: {grading_result}")
            
            # 直接设置主观题得分 - 修复键名
            total_score = grading_result.get('_total_score', 0)  # 使用正确的键名
            student.subjective_score = total_score
            
            # 更新总分
            student.score = student.objective_score + student.subjective_score
            show_progress(f"主观题得分: {total_score}，总分: {student.score}", gui_window=gui_window)
            
            # 生成主观题报告
            show_progress("正在写入主观题报告...", gui_window=gui_window)
            _generate_subjective_report_direct(student, grading_result, gui_window)
            
            # 重置进度条状态，显示完成信息
            if gui_window is not None:
                try:
                    if hasattr(gui_window, 'progress_bar'):
                        gui_window.progress_bar.setFormat("✅ 主观题评分完成")
                        from PySide6.QtWidgets import QApplication
                        QApplication.processEvents()
                except Exception as e:
                    print(f"GUI进度条重置失败: {e}")
        else:
            show_progress("主观题阅卷失败，结果为空", gui_window=gui_window)
            student.add_recognition_log("主观题阅卷失败，结果为空")
            
    except Exception as e:
        show_progress(f"主观题阅卷异常: {str(e)}", gui_window=gui_window)
        student.add_recognition_log(f"主观题阅卷异常: {str(e)}")


def _generate_subjective_report_direct(student: StudentInfo, grading_result: dict, gui_window=None):
    """
    生成主观题报告（直接处理版本）
    
    参数:
        student: 学生信息对象
        grading_result: 主观题评分结果
        gui_window: GUI窗口实例（可选）
    """
    try:
        # 添加调试信息
        print("🔍 生成主观题报告调试:")
        print(f"student.name: {student.name}")
        print(f"student.student_id: {student.student_id}")
        print(f"grading_result: {grading_result}")
        
        # 生成报告时支持部分识别：缺失的字段用默认占位
        default_name = "未识别姓名"
        default_id = "未识别学号"
        final_name = student.name if student.name else default_name
        final_id = student.student_id if student.student_id else default_id

        # 显示状态信息：区分完全识别、部分识别、完全未识别
        if student.name and student.student_id:
            show_progress(f"使用识别的学生信息生成报告: {final_name} ({final_id})", gui_window=gui_window)
        elif student.name or student.student_id:
            show_progress(f"使用部分识别的学生信息生成报告: {final_name} ({final_id})", gui_window=gui_window)
        else:
            show_progress(f"使用默认学生信息生成报告: {final_name} ({final_id})", gui_window=gui_window)

        # 生成报告
        report_path = generate_subjective_report_direct(
            student, grading_result, final_name, final_id
        )
        if report_path:
            show_progress(f"主观题报告生成成功: {os.path.basename(report_path)}", gui_window=gui_window)
            student.add_recognition_log(f"主观题报告已生成: {report_path}")
        else:
            show_progress("主观题报告生成失败", gui_window=gui_window)
            student.add_recognition_log("主观题报告生成失败")
                
    except Exception as e:
        student.add_recognition_log(f"报告生成异常: {str(e)}")


def omr_processing(image_path: str, answer_key: dict, api_key: str, subjective_answer_file: str = None, 
                  recognition_mode: str = "B", enable_subjective: bool = True, enable_objective: bool = True, enable_student_info: bool = True, question_types: dict = None, question_types_file: str = None, answer_config_file: str = None, subjective_config: dict = None, gui_window=None) -> StudentInfo:
    """
    OMR处理主函数，支持客观题和主观题阅卷
    
    参数:
        image_path: 答题卡图片路径
        answer_key: 客观题答案配置
        api_key: API密钥
        subjective_answer_file: 主观题答案文件路径（可选）
        recognition_mode: 识别模式，"A"为自然顺序，"B"为列优先顺序，默认为"B"
        enable_subjective: 是否启用主观题评分，默认为True
        enable_objective: 是否启用客观题评分，默认为True
        enable_student_info: 是否启用学生信息识别，默认为True
        question_types: 题目类型配置（可选）
        question_types_file: 题目类型配置文件路径（可选）
        answer_config_file: 答案配置文件路径（可选，用于获取选项数量配置）
        
    返回:
        StudentInfo: 包含识别结果的学生信息对象
    """
    student = StudentInfo()
    student.image_path = image_path  # 设置图片路径
    
    try:
        show_progress("开始处理试卷图片...", gui_window=gui_window)
        
        # 0. 图像纠偏
        show_progress("正在进行图像纠偏...", gui_window=gui_window)
        processing_image_path = image_path
        try:
            # 读取原始图片
            original_img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if original_img is None:
                raise ValueError(f"无法读取图片: {image_path}")
            
            # 执行纠偏
            deskewed_img = deskew_image(original_img)
            
            # 保存纠偏后的图片到临时目录
            # 使用 temp_deskewed 目录，并保持原始文件名，以便后续流程能正确获取文件名
            temp_deskew_dir = Path("temp_deskewed")
            temp_deskew_dir.mkdir(parents=True, exist_ok=True)
            
            # 清理旧的临时文件(可选，防止堆积)
            # for f in temp_deskew_dir.glob('*'):
            #     try: f.unlink()
            #     except: pass
            
            original_name = Path(image_path).name
            deskewed_path = temp_deskew_dir / original_name
            
            # 保存图片
            is_success, im_buf_arr = cv2.imencode(".jpg", deskewed_img)
            im_buf_arr.tofile(str(deskewed_path))
            
            processing_image_path = str(deskewed_path)
            print(f"图像纠偏完成，保存至: {processing_image_path}")
            
        except Exception as e:
            print(f"图像纠偏失败，将使用原图: {e}")
            processing_image_path = image_path

        # 1. 准备图片文件
        show_progress("正在准备图片文件...", gui_window=gui_window)
        target_path = prepare_image_file(processing_image_path)
        
        # 2. 清理检测目录
        show_progress("正在清理检测目录...", gui_window=gui_window)
        clean_detect_dir()
        
        # 3. 解析题目类型配置
        show_progress("正在解析题目类型配置...", gui_window=gui_window)
        if question_types_file and os.path.exists(question_types_file):
            question_types = parse_question_types(question_types_file)
        show_progress(f"题目类型配置解析完成", gui_window=gui_window)
        
        # 4. 处理客观题
        if enable_objective:
            show_progress("开始客观题阅卷流程...", gui_window=gui_window)
            process_objective_questions(
                student=student,
                answer_key=answer_key,
                question_types=question_types,
                recognition_mode=recognition_mode,
                question_types_file=question_types_file,
                original_image_path=processing_image_path,
                answer_config_file=answer_config_file,
                gui_window=gui_window
            )
        else:
            show_progress("客观题评分已禁用，跳过客观题阅卷", gui_window=gui_window)
        
        # 5. 处理学生信息识别
        if enable_student_info:
            process_student_info(student, processing_image_path, api_key, gui_window)
        else:
            show_progress("学生信息识别已禁用，跳过学生信息识别", gui_window=gui_window)
        
        # 6. 处理主观题
        if enable_subjective and subjective_answer_file:
            process_subjective_questions(
                student=student,
                subjective_answer_file=subjective_answer_file,
                api_key=api_key,
                subjective_config=subjective_config,  # 传递主观题配置
                gui_window=gui_window,
                image_path=processing_image_path
            )
        else:
            show_progress("主观题评分已禁用，跳过主观题阅卷", gui_window=gui_window)
        
        show_progress("试卷处理完成！", gui_window=gui_window)
        return student
        
    except Exception as e:
        show_progress(f"处理异常: {str(e)}", gui_window=gui_window)
        student.add_recognition_log(f"处理异常: {str(e)}")
        raise

    return student
