import os
import sys
import cv2
import numpy as np
import tempfile
import shutil
from pathlib import Path

# 导入本地模块
from core.omr.recognizer import recognize_answer_sheet, detect_rectangle_filling
from core.omr.detector import run as yolo_detect
from core.omr.question_parser import parse_question_types
from utils.path_utils import get_project_root, get_resource_path

class AnswerRecognizer:
    """
    答题卡识别器
    整合YOLO检测和答案识别功能
    """
    
    def __init__(self, weights_path=None, question_types_file=None):
        """
        初始化识别器
        
        参数:
            weights_path: YOLO模型权重文件路径，默认使用best.pt
            question_types_file: 题目类型配置文件路径
        """
        # 设置模型权重路径
        if weights_path is None:
            # 使用配置目录下的权重文件 (支持打包环境)
            weights_path = get_resource_path(os.path.join("config", "weights", "best.pt"))
        
        self.weights_path = weights_path
        
        # 加载题目类型配置
        self.question_types = {}
        if question_types_file and os.path.exists(question_types_file):
            try:
                self.question_types = parse_question_types(question_types_file)
                print(f"已加载题目类型配置: {len(self.question_types)} 个题目")
            except Exception as e:
                print(f"加载题目类型配置失败: {e}，使用默认配置")
        else:
            print("使用默认配置（所有题目为单选题）")
    
    def recognize(self, image_path):
        """
        识别答题卡
        
        参数:
            image_path: 答题卡图片路径
        
        返回:
            dict: 识别结果
        """
        try:
            # 创建临时工作目录
            temp_dir = tempfile.mkdtemp(prefix="answer_recognition_")
            
            # 复制输入图片到临时目录
            temp_input = os.path.join(temp_dir, "input.jpg")
            # 检查输入文件是否存在
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Input image not found: {image_path}")
            shutil.copy2(image_path, temp_input)
            
            # 第一步：使用YOLO检测答题区域
            yolo_output_dir = os.path.join(temp_dir, "yolo_output")
            
            # 调用YOLO检测
            yolo_detect(
                weights=self.weights_path,
                source=temp_input,
                project=yolo_output_dir,
                name="detect",
                save_crop=True,
                save_txt=True,
                conf_thres=0.5,
                exist_ok=True,
                nosave=False
            )
            
            # 检查YOLO检测结果
            crops_dir = os.path.join(yolo_output_dir, "detect", "crops", "answerArea")
            
            if not os.path.exists(crops_dir) or not os.listdir(crops_dir):
                # 如果YOLO没有检测到答题区域，直接对整张图片进行识别
                print("YOLO未检测到答题区域，直接识别整张图片")
                result = self._recognize_single_image(temp_input)
                return {
                    'detection_method': 'direct',
                    'total_questions': len(result),
                    'answers': result
                }
            
            # 第二步：识别每个检测到的答题区域
            all_results = {}
            crop_files = sorted([f for f in os.listdir(crops_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
            
            print(f"检测到 {len(crop_files)} 个答题区域")
            
            for i, crop_file in enumerate(crop_files):
                crop_path = os.path.join(crops_dir, crop_file)
                
                # 计算起始题号
                # 题号映射：1-25题对应前5张图片，31-80题对应第6-15张图片
                if i < 5:
                    # 前5张图片对应1-25题
                    start_question_num = i * 5 + 1
                else:
                    # 第6-15张图片对应31-80题
                    start_question_num = 31 + (i - 5) * 5
                
                # 识别当前区域的答案
                region_result = recognize_answer_sheet(
                    crop_path,
                    question_types=self.question_types,
                    start_question_num=start_question_num
                )
                
                # 合并结果
                all_results.update(region_result)
                
                print(f"区域 {i+1} ({crop_file}) 识别完成，题目 {start_question_num}-{start_question_num+4}")
            
            return {
                'detection_method': 'yolo',
                'detected_regions': len(crop_files),
                'total_questions': len(all_results),
                'answers': all_results
            }
            
        except Exception as e:
            print(f"识别过程中出现错误: {e}")
            raise
        
        finally:
            # 清理临时目录
            if 'temp_dir' in locals() and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
    
    def _recognize_single_image(self, image_path):
        """
        直接识别单张图片（不使用YOLO检测）
        
        参数:
            image_path: 图片路径
        
        返回:
            dict: 识别结果
        """
        return recognize_answer_sheet(
            image_path,
            question_types=self.question_types,
            start_question_num=1
        )
    
    def format_result(self, raw_result):
        """
        格式化识别结果为标准JSON格式
        
        参数:
            raw_result: 原始识别结果
        
        返回:
            dict: 格式化后的结果
        """
        formatted_answers = []
        
        if 'answers' in raw_result:
            for question_num, answer in raw_result['answers'].items():
                if isinstance(question_num, int):
                    question_type = self.question_types.get(question_num, 'single')
                    
                    formatted_answer = {
                        'question_number': question_num,
                        'question_type': question_type,
                        'answer': answer if answer else ([] if question_type == 'multiple' else ""),
                        'is_filled': bool(answer)
                    }
                    
                    formatted_answers.append(formatted_answer)
        
        # 按题号排序
        formatted_answers.sort(key=lambda x: x['question_number'])
        
        return {
            'detection_method': raw_result.get('detection_method', 'unknown'),
            'detected_regions': raw_result.get('detected_regions', 0),
            'total_questions': len(formatted_answers),
            'answers': formatted_answers,
            'summary': {
                'filled_count': sum(1 for ans in formatted_answers if ans['is_filled']),
                'empty_count': sum(1 for ans in formatted_answers if not ans['is_filled']),
                'single_choice_count': sum(1 for ans in formatted_answers if ans['question_type'] == 'single'),
                'multiple_choice_count': sum(1 for ans in formatted_answers if ans['question_type'] == 'multiple')
            }
        }

# 测试函数
if __name__ == "__main__":
    # 测试识别器
    recognizer = AnswerRecognizer()
    
    # 测试图片路径
    test_image = r"E:\code_space\code_python\MarkingSystem\test_img\answer_125.jpg"
    
    if os.path.exists(test_image):
        print(f"测试图片: {test_image}")
        result = recognizer.recognize(test_image)
        formatted_result = recognizer.format_result(result)
        
        print("\n=== 识别结果 ===")
        print(f"检测方法: {formatted_result['detection_method']}")
        print(f"检测区域数: {formatted_result['detected_regions']}")
        print(f"总题目数: {formatted_result['total_questions']}")
        
        print("\n=== 答案详情 ===")
        for answer in formatted_result['answers']:
            print(f"题目 {answer['question_number']} ({answer['question_type']}): {answer['answer']} {'✓' if answer['is_filled'] else '✗'}")
        
        print("\n=== 统计信息 ===")
        summary = formatted_result['summary']
        print(f"已填涂: {summary['filled_count']} 题")
        print(f"未填涂: {summary['empty_count']} 题")
        print(f"单选题: {summary['single_choice_count']} 题")
        print(f"多选题: {summary['multiple_choice_count']} 题")
    else:
        print(f"测试图片不存在: {test_image}")