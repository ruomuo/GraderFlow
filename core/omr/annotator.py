"""
图片标注模块
用于在答题卡图片上添加错题号和总分信息
"""

import cv2
import os
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import shutil
import pandas as pd
from utils.image_io import imread_safe, imwrite_safe


def save_grading_records(student_info, output_dir: str = "read") -> str:
    """
    保存客观题阅卷记录到CSV文件
    
    参数:
        student_info: StudentInfo对象
        output_dir: 输出目录，默认为"read"
        
    返回:
        str: CSV文件的保存路径
    """
    try:
        # 确保输出目录存在
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 生成输出文件名
        if student_info.name and student_info.student_id:
            # 使用安全的文件名
            safe_name = student_info.name.replace(" ", "_")
            safe_id = student_info.student_id.replace(" ", "_")
            output_filename = f"{safe_name}_{safe_id}_records.csv"
        else:
            # 未识别姓名/学号时，使用原图文件名
            try:
                original_name = Path(getattr(student_info, "image_path", "")).stem
                if not original_name:
                    original_name = "grading_records"
            except Exception:
                original_name = "grading_records"
            output_filename = f"{original_name}_records.csv"
        
        output_file_path = output_path / output_filename
        
        # 准备数据
        data = []
        # 获取所有相关题号并排序
        all_questions = set()
        if student_info.answers:
            all_questions.update(student_info.answers.keys())
        if student_info.correct_answers:
            all_questions.update(student_info.correct_answers.keys())
        
        sorted_questions = sorted(list(all_questions))
        
        for q_num in sorted_questions:
            # 获取学生答案
            user_ans = student_info.answers.get(q_num, "未填涂")
            if isinstance(user_ans, list):
                user_ans = "".join(user_ans)
            
            # 获取正确答案
            correct_info = student_info.correct_answers.get(q_num, {})
            correct_ans = correct_info.get('answer', "") if correct_info else ""
            if isinstance(correct_ans, list):
                correct_ans = "".join(correct_ans)
            elif isinstance(correct_ans, str):
                correct_ans = correct_ans
            
            # 获取得分
            score = student_info.question_scores.get(q_num, 0.0)
            
            # 确定状态
            if q_num in student_info.wrong_questions:
                status = "错误"
            elif q_num in student_info.blank_questions:
                status = "空白"
            elif user_ans == "未填涂":
                status = "空白"
            elif user_ans == correct_ans: # 简单比较，实际上calculate_score已经处理了逻辑
                 status = "正确"
            else:
                 # 如果没在wrong_questions也没在blank_questions，且有分，那就是正确
                 # 但为了保险，还是依赖question_scores判断
                 if score > 0:
                     status = "正确"
                 else:
                     status = "错误"

            data.append({
                "题号": q_num,
                "学生答案": user_ans,
                "正确答案": correct_ans,
                "得分": score,
                "状态": status
            })
            
        # 创建DataFrame并保存
        if data:
            df = pd.DataFrame(data)
            df.to_csv(output_file_path, index=False, encoding='utf-8-sig')
            print(f"阅卷记录已保存: {output_file_path}")
            return str(output_file_path)
        else:
            print("没有阅卷数据可保存")
            return None
            
    except Exception as e:
        print(f"保存阅卷记录失败: {str(e)}")
        return None


def annotate_answer_sheet(image_path: str, student_info, output_dir: str = "read") -> str:
    """
    在答题卡图片上标注错题号和总分信息，并保存到指定目录
    
    参数:
        image_path: 原始答题卡图片路径
        student_info: StudentInfo对象，包含评分结果
        output_dir: 输出目录，默认为"read"
        
    返回:
        str: 标注后图片的保存路径
    """
    try:
        print(f"DEBUG: 开始执行 annotate_answer_sheet, image_path={image_path}")
        # 确保输出目录存在
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 读取图片 (支持中文路径)
        # img = cv2.imread(image_path)
        img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            print(f"DEBUG: 读取图片失败: {image_path}")
            raise ValueError(f"无法读取图片: {image_path}")
        
        # 获取图片尺寸
        height, width = img.shape[:2]

        # 1. 绘制填涂痕迹 (根据检测框和填涂框位置)
        if hasattr(student_info, 'detailed_answers') and student_info.detailed_answers:
            print(f"正在绘制填涂痕迹...")
            try:
                for filename, file_details in student_info.detailed_answers.items():
                    # 检查file_details是否为字典（如果是扁平结构，可能这里会报错）
                    if not isinstance(file_details, dict):
                         # 兼容旧的扁平结构 {q_num: details}
                         # 如果filename是题号(int)，file_details是details(list/dict)
                         if isinstance(filename, int):
                             q_num = filename
                             options_list = file_details
                             # 处理单个题目的选项
                             if isinstance(options_list, list):
                                 for opt in options_list:
                                     if 'global_position' in opt and opt['global_position']:
                                         gn_x, gn_y, gn_w, gn_h = opt['global_position']
                                         px, py = int(gn_x * width), int(gn_y * height)
                                         pw, ph = int(gn_w * width), int(gn_h * height)
                                         if opt.get('filled', False):
                                             cv2.rectangle(img, (px, py), (px+pw, py+ph), (0, 255, 0), 2)
                             continue
                         else:
                             print(f"警告: 详细结果结构不符合预期 (key={filename}, type={type(file_details)})")
                             continue

                    for q_num, options_list in file_details.items():
                        # 获取正确答案信息
                        is_wrong = q_num in student_info.wrong_questions
                        is_blank = q_num in student_info.blank_questions
                        
                        correct_ans_list = []
                        if is_wrong or is_blank:
                            correct_info = student_info.correct_answers.get(q_num, {})
                            correct_ans = correct_info.get('answer', "")
                            if isinstance(correct_ans, str):
                                correct_ans_list = list(correct_ans) # 'A' -> ['A'], 'AB' -> ['A', 'B']
                            elif isinstance(correct_ans, list):
                                correct_ans_list = correct_ans

                        for opt in options_list:
                            # 检查是否有全局坐标
                            if 'global_position' in opt and opt['global_position']:
                                gn_x, gn_y, gn_w, gn_h = opt['global_position']
                                
                                # 转换为像素坐标
                                px = int(gn_x * width)
                                py = int(gn_y * height)
                                pw = int(gn_w * width)
                                ph = int(gn_h * height)
                                
                                # 1. 标记已填涂的选项 (绿色矩形框)
                                if opt.get('filled', False):
                                    cv2.rectangle(img, (px, py), (px+pw, py+ph), (0, 255, 0), 2)

                                # 2. 如果是错题或空白题，在正确选项位置标记红色答案
                                if (is_wrong or is_blank) and opt.get('option') in correct_ans_list:
                                    # 绘制红色文字 (例如 "A")
                                    text = opt.get('option')
                                    # 计算中心位置
                                    cx = px + pw // 2
                                    cy = py + ph // 2
                                    
                                    # 字体设置
                                    text_scale = 1.0  # 稍微大一点
                                    text_thickness = 3 # 加粗
                                    font_face = cv2.FONT_HERSHEY_SIMPLEX
                                    
                                    (text_w, text_h), _ = cv2.getTextSize(text, font_face, text_scale, text_thickness)
                                    text_x = cx - text_w // 2
                                    text_y = cy + text_h // 2
                                    
                                    # 绘制文字
                                    cv2.putText(img, text, (text_x, text_y), font_face, text_scale, (0, 0, 255), text_thickness)
            except Exception as e:
                print(f"绘制填涂痕迹时出错: {e}")
                import traceback
                traceback.print_exc()
        
        # 准备标注信息
        wrong_questions = student_info.wrong_questions
        blank_questions = student_info.blank_questions
        total_score = student_info.score
        objective_score = student_info.objective_score
        
        # 设置字体和颜色
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0
        thickness = 2
        
        # 错题信息颜色（红色）
        error_color = (0, 0, 255)
        # 总分信息颜色（蓝色）
        score_color = (255, 0, 0)
        # 背景色（白色）
        bg_color = (255, 255, 255)
        
        # 在图片顶部添加总分信息
        # 整合姓名、学号、总分信息
        summary_lines = []
        if student_info.name:
            summary_lines.append(f"Name: {student_info.name}")
        if student_info.student_id:
            summary_lines.append(f"ID: {student_info.student_id}")
            
        score_text = f"Total Score: {total_score:.1f}"
        if objective_score > 0:
            score_text += f" (Obj: {objective_score:.1f})"
        summary_lines.append(score_text)
        
        # 计算摘要区域大小
        max_text_width = 0
        total_text_height = 0
        line_heights = []
        
        for line in summary_lines:
            (t_w, t_h), _ = cv2.getTextSize(line, font, font_scale, thickness)
            max_text_width = max(max_text_width, t_w)
            total_text_height += t_h + 10 # 10px spacing
            line_heights.append(t_h)
            
        # 绘制背景
        box_x, box_y = 10, 10
        box_w = max_text_width + 40
        box_h = total_text_height + 20
        
        cv2.rectangle(img, (box_x, box_y), (box_x + box_w, box_y + box_h), bg_color, -1)
        cv2.rectangle(img, (box_x, box_y), (box_x + box_w, box_y + box_h), score_color, 2)
        
        # 绘制每一行文字
        current_y = box_y + 25
        for i, line in enumerate(summary_lines):
            cv2.putText(img, line, (box_x + 20, current_y), font, font_scale, score_color, thickness)
            current_y += line_heights[i] + 10
            
        # 记录已占用的Y坐标，供后续错题信息使用
        y_offset = box_y + box_h + 20
        
        # 添加错题信息
        if wrong_questions or blank_questions:
            # y_offset = 60  # 已由上方动态计算
            
            if wrong_questions:
                wrong_text = f"Wrong Questions: {', '.join(map(str, sorted(wrong_questions)))}"
                # 如果错题太多，分行显示
                if len(wrong_text) > 80:
                    wrong_nums = sorted(wrong_questions)
                    # 每行最多显示15个题号
                    lines = []
                    for i in range(0, len(wrong_nums), 15):
                        line_nums = wrong_nums[i:i+15]
                        if i == 0:
                            lines.append(f"Wrong Questions: {', '.join(map(str, line_nums))}")
                        else:
                            lines.append(f"                {', '.join(map(str, line_nums))}")
                    
                    for line in lines:
                        (line_width, line_height), _ = cv2.getTextSize(line, font, font_scale * 0.8, thickness)
                        # 绘制背景
                        cv2.rectangle(img, (10, y_offset), (10 + line_width + 20, y_offset + line_height + 10), bg_color, -1)
                        cv2.rectangle(img, (10, y_offset), (10 + line_width + 20, y_offset + line_height + 10), error_color, 2)
                        # 绘制文字
                        cv2.putText(img, line, (20, y_offset + line_height), font, font_scale * 0.8, error_color, thickness)
                        y_offset += line_height + 20
                else:
                    (wrong_width, wrong_height), _ = cv2.getTextSize(wrong_text, font, font_scale * 0.8, thickness)
                    # 绘制背景
                    cv2.rectangle(img, (10, y_offset), (10 + wrong_width + 20, y_offset + wrong_height + 10), bg_color, -1)
                    cv2.rectangle(img, (10, y_offset), (10 + wrong_width + 20, y_offset + wrong_height + 10), error_color, 2)
                    # 绘制文字
                    cv2.putText(img, wrong_text, (20, y_offset + wrong_height), font, font_scale * 0.8, error_color, thickness)
                    y_offset += wrong_height + 30
            
            if blank_questions:
                blank_text = f"Blank Questions: {', '.join(map(str, sorted(blank_questions)))}"
                # 如果空白题太多，分行显示
                if len(blank_text) > 80:
                    blank_nums = sorted(blank_questions)
                    # 每行最多显示15个题号
                    lines = []
                    for i in range(0, len(blank_nums), 15):
                        line_nums = blank_nums[i:i+15]
                        if i == 0:
                            lines.append(f"Blank Questions: {', '.join(map(str, line_nums))}")
                        else:
                            lines.append(f"                {', '.join(map(str, line_nums))}")
                    
                    for line in lines:
                        (line_width, line_height), _ = cv2.getTextSize(line, font, font_scale * 0.8, thickness)
                        # 绘制背景（橙色边框）
                        orange_color = (0, 165, 255)
                        cv2.rectangle(img, (10, y_offset), (10 + line_width + 20, y_offset + line_height + 10), bg_color, -1)
                        cv2.rectangle(img, (10, y_offset), (10 + line_width + 20, y_offset + line_height + 10), orange_color, 2)
                        # 绘制文字
                        cv2.putText(img, line, (20, y_offset + line_height), font, font_scale * 0.8, orange_color, thickness)
                        y_offset += line_height + 20
                else:
                    (blank_width, blank_height), _ = cv2.getTextSize(blank_text, font, font_scale * 0.8, thickness)
                    # 绘制背景（橙色边框）
                    orange_color = (0, 165, 255)
                    cv2.rectangle(img, (10, y_offset), (10 + blank_width + 20, y_offset + blank_height + 10), bg_color, -1)
                    cv2.rectangle(img, (10, y_offset), (10 + blank_width + 20, y_offset + blank_height + 10), orange_color, 2)
                    # 绘制文字
                    cv2.putText(img, blank_text, (20, y_offset + blank_height), font, font_scale * 0.8, orange_color, thickness)
        
        # 生成输出文件名
        original_name = Path(image_path).stem
        if student_info.name and student_info.student_id:
            # 使用安全的文件名，避免中文编码问题
            safe_name = student_info.name.replace(" ", "_")
            safe_id = student_info.student_id.replace(" ", "_")
            output_filename = f"{safe_name}_{safe_id}_annotated.jpg"
        else:
            output_filename = f"{original_name}_annotated.jpg"
        
        output_file_path = output_path / output_filename
        
        # 保存标注后的图片
        # success = cv2.imwrite(str(output_file_path), img)
        is_success, im_buf_arr = cv2.imencode(".jpg", img)
        im_buf_arr.tofile(str(output_file_path))
        success = True
        
        if not success:
            raise ValueError(f"保存图片失败: {output_file_path}")
        
        print(f"标注图片已保存: {output_file_path}")
        return str(output_file_path)
        
    except Exception as e:
        print(f"图片标注失败: {str(e)}")
        return None


def copy_original_to_read(image_path: str, student_info, output_dir: str = "read") -> str:
    """
    将原始答题卡复制到read文件夹（作为备份）
    
    参数:
        image_path: 原始答题卡图片路径
        student_info: StudentInfo对象
        output_dir: 输出目录，默认为"read"
        
    返回:
        str: 复制后图片的保存路径
    """
    try:
        # 确保输出目录存在
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 生成输出文件名
        original_name = Path(image_path).stem
        if student_info.name and student_info.student_id:
            # 使用安全的文件名，避免中文编码问题
            safe_name = student_info.name.replace(" ", "_")
            safe_id = student_info.student_id.replace(" ", "_")
            output_filename = f"{safe_name}_{safe_id}_original.jpg"
        else:
            output_filename = f"{original_name}_original.jpg"
        
        output_file_path = output_path / output_filename
        
        # 复制原始图片
        shutil.copy2(image_path, output_file_path)
        
        print(f"原始图片已复制: {output_file_path}")
        return str(output_file_path)
        
    except Exception as e:
        print(f"复制原始图片失败: {str(e)}")
        return None


def create_summary_image(student_info, output_dir: str = "read") -> str:
    """
    创建一个包含详细评分信息的摘要图片
    
    参数:
        student_info: StudentInfo对象
        output_dir: 输出目录，默认为"read"
        
    返回:
        str: 摘要图片的保存路径
    """
    try:
        # 确保输出目录存在
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 创建一个白色背景的图片
        img_width, img_height = 800, 600
        img = np.ones((img_height, img_width, 3), dtype=np.uint8) * 255
        
        # 设置字体参数
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.8
        thickness = 2
        line_height = 30
        
        # 颜色定义
        title_color = (0, 0, 0)      # 黑色
        score_color = (0, 128, 0)    # 绿色
        error_color = (0, 0, 255)    # 红色
        warning_color = (0, 165, 255) # 橙色
        
        y_pos = 50
        
        # 标题
        title = "Answer Sheet Grading Summary"
        cv2.putText(img, title, (50, y_pos), font, 1.2, title_color, 3)
        y_pos += 60
        
        # 学生信息
        name_text = f"Name: {student_info.name if student_info.name else 'Not Recognized'}"
        cv2.putText(img, name_text, (50, y_pos), font, font_scale, title_color, thickness)
        y_pos += line_height
        
        id_text = f"Student ID: {student_info.student_id if student_info.student_id else 'Not Recognized'}"
        cv2.putText(img, id_text, (50, y_pos), font, font_scale, title_color, thickness)
        y_pos += line_height + 20
        
        # 分数信息
        total_text = f"Total Score: {student_info.score:.1f}"
        cv2.putText(img, total_text, (50, y_pos), font, font_scale, score_color, thickness)
        y_pos += line_height
        
        if student_info.objective_score > 0:
            obj_text = f"Objective Score: {student_info.objective_score:.1f}"
            cv2.putText(img, obj_text, (50, y_pos), font, font_scale, score_color, thickness)
            y_pos += line_height
        
        if student_info.subjective_score > 0:
            subj_text = f"Subjective Score: {student_info.subjective_score:.1f}"
            cv2.putText(img, subj_text, (50, y_pos), font, font_scale, score_color, thickness)
            y_pos += line_height
        
        y_pos += 20
        
        # 错题信息
        if student_info.wrong_questions:
            wrong_title = f"Wrong Questions ({len(student_info.wrong_questions)}):"
            cv2.putText(img, wrong_title, (50, y_pos), font, font_scale, error_color, thickness)
            y_pos += line_height
            
            # 分行显示错题号
            wrong_nums = sorted(student_info.wrong_questions)
            for i in range(0, len(wrong_nums), 20):  # 每行20个题号
                line_nums = wrong_nums[i:i+20]
                wrong_line = ', '.join(map(str, line_nums))
                cv2.putText(img, wrong_line, (70, y_pos), font, font_scale * 0.9, error_color, thickness)
                y_pos += line_height
        
        # 空白题信息
        if student_info.blank_questions:
            y_pos += 10
            blank_title = f"Blank Questions ({len(student_info.blank_questions)}):"
            cv2.putText(img, blank_title, (50, y_pos), font, font_scale, warning_color, thickness)
            y_pos += line_height
            
            # 分行显示空白题号
            blank_nums = sorted(student_info.blank_questions)
            for i in range(0, len(blank_nums), 20):  # 每行20个题号
                line_nums = blank_nums[i:i+20]
                blank_line = ', '.join(map(str, line_nums))
                cv2.putText(img, blank_line, (70, y_pos), font, font_scale * 0.9, warning_color, thickness)
                y_pos += line_height
        
        # 生成输出文件名
        if student_info.name and student_info.student_id:
            # 使用安全的文件名，避免中文编码问题
            safe_name = student_info.name.replace(" ", "_")
            safe_id = student_info.student_id.replace(" ", "_")
            output_filename = f"{safe_name}_{safe_id}_summary.jpg"
        else:
            # 未识别姓名/学号时，使用原图文件名
            try:
                original_name = Path(getattr(student_info, "image_path", "")).stem
                if not original_name:
                    original_name = "grading_summary"
            except Exception:
                original_name = "grading_summary"
            output_filename = f"{original_name}_summary.jpg"
        
        output_file_path = output_path / output_filename
        
        # 保存摘要图片
        success = imwrite_safe(str(output_file_path), img)
        if not success:
            raise ValueError(f"保存摘要图片失败: {output_file_path}")
        
        print(f"评分摘要图片已保存: {output_file_path}")
        return str(output_file_path)
        
    except Exception as e:
        print(f"创建摘要图片失败: {str(e)}")
        return None