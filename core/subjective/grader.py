#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主观题阅卷模块 - 直接处理版本
直接将答案文件内容传递给大模型，不进行格式解析
"""

from PIL import Image
import io
import base64
import re
import json
from openai import OpenAI
import os
from pathlib import Path
from datetime import datetime
from utils.config_manager import config_manager

# 注释：原有的单独检测函数已被合并到主评分函数中，不再使用
# def _detect_subjective_questions_in_image(image_base64, answer_content, api_key):
#     """
#     检测答题卡图片中是否存在主观题内容 - 已废弃，功能已合并到主评分函数中
#     """
#     pass


def convert_image_to_webp_base64(input_image_path):
    """将图片转换为webp格式的base64编码（优化版本）"""
    try:
        with Image.open(input_image_path) as img:
            # 优化图像尺寸以提高处理速度
            max_size = (1920, 1080)  # 限制最大尺寸
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                print(f"🔧 图像已缩放至: {img.size}")
            
            # 转换为RGB模式（如果需要）
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            byte_arr = io.BytesIO()
            # 使用较高的质量但不是最高，平衡文件大小和质量
            img.save(byte_arr, format='webp', quality=85, optimize=True)
            byte_arr = byte_arr.getvalue()
            base64_str = base64.b64encode(byte_arr).decode('utf-8')
            print(f"🔧 图像压缩后大小: {len(base64_str)} 字符")
            return base64_str
    except IOError as e:
        print(f"❌ 图片转换失败: {input_image_path}, 错误: {e}")
        return None

def grade_subjective_questions_direct(image_path, answer_content, api_key, user_prompts=None):
    """
    直接对主观题进行评分，不解析答案格式
    
    Args:
        image_path: 答题卡图片路径
        answer_content: 主观题答案文件的原始内容
        api_key: API密钥
        user_prompts: 用户自定义提示词字典，格式为 {题号: 提示词}
        
    Returns:
        dict: 评分结果
        {
            '_total_score': int,  # 总分
            '_full_report': str   # 完整评分报告
        }
    """
    print(f"🔍 开始主观题阅卷...")
    print(f"📷 图片路径: {image_path}")
    print(f"📄 答案内容长度: {len(answer_content)} 字符")
    print(f"📄 答案内容前100字: {answer_content[:100]}...")
    
    if not answer_content.strip():
        print("❌ 答案内容为空，跳过评分")
        return {}
    
    try:
        print("🔄 转换图片为base64格式...")
        # 转换图片为base64
        image_base64 = convert_image_to_webp_base64(image_path)
        if not image_base64:
            print("❌ 图片转换失败")
            return {}
        
        print(f"✅ 图片转换成功，base64长度: {len(image_base64)} 字符")
        
        # 构建优化的评分提示（合并检测和评分）
        base_prompt = f"""请分析这张答题卡图片：

1. 首先检测是否存在主观题内容（手写文字答案）
2. 如果存在主观题，则进行评分；如果不存在，返回"无主观题内容"

标准答案：
{answer_content}

评分要求：
- 只评分主观题（手写答案部分）
- 简洁准确地指出扣分点
- 给出具体分数和扣分原因"""

        # 添加用户自定义提示词
        if user_prompts:
            print(f"🎯 应用用户自定义提示词: {len(user_prompts)} 条")
            user_prompt_section = "\n\n用户要求：\n"
            for q_num, prompt in user_prompts.items():
                if prompt.strip():
                    user_prompt_section += f"第{q_num}题：{prompt}\n"
            base_prompt += user_prompt_section

        # 简化的输出格式要求
        prompt = base_prompt + f"""

输出格式：
如果检测到主观题内容，请按以下格式输出：
题目X：[扣分点]，得分：X/X分
...
总分：<total>X</total>

如果未检测到主观题内容，请输出：
无主观题内容
<total>0</total>
"""

        # 调用API（添加超时机制）
        import time
        from openai import OpenAI
        
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.siliconflow.cn/v1",
            timeout=90  # 设置90秒超时
        )
        
        # 从配置文件读取模型名称
        model_name = config_manager.get("model_name", "Qwen/Qwen2.5-VL-72B-Instruct")
        print(f"🤖 调用模型: {model_name}")
        print(f"📝 提示词长度: {len(prompt)} 字符")
        
        start_time = time.time()
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/webp;base64,{image_base64}"}}
                        ]
                    }
                ],
                temperature=0.1,
                max_tokens=1000  # 减少token数量，提高响应速度
            )
            
            elapsed_time = time.time() - start_time
            print(f"⏱️ API调用耗时: {elapsed_time:.2f}秒")
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            if elapsed_time >= 90:
                print(f"⏰ API调用超时 ({elapsed_time:.2f}秒)，跳到下一步")
                return {
                    '_total_score': 0,
                    '_full_report': f"API调用超时（{elapsed_time:.2f}秒），跳过本题评分"
                }
            else:
                print(f"❌ API调用失败: {str(e)}")
                raise e
        
        result_text = response.choices[0].message.content
        print(f"📊 模型输出前100字: {result_text[:100]}...")
        print(f"📊 模型输出总长度: {len(result_text)} 字符")
        
        # 添加完整模型输出的调试信息
        print("=" * 50)
        print("🔍 模型完整输出内容:")
        print(result_text)
        print("=" * 50)
        
        # 解析总分
        print("🔍 解析总分...")
        total_score = 0
        
        # 尝试多种总分解析方式
        total_patterns = [
            r'<total>(\d+)</total>',  # 标准格式
            r'总分[：:]?\s*(\d+)',     # 中文总分
            r'总得分[：:]?\s*(\d+)',   # 中文总得分
            r'合计[：:]?\s*(\d+)',     # 中文合计
            r'Total[：:]?\s*(\d+)',   # 英文Total
        ]
        
        for pattern in total_patterns:
            total_match = re.search(pattern, result_text, re.IGNORECASE)
            if total_match:
                total_score = int(total_match.group(1))
                print(f"✅ 使用模式 '{pattern}' 成功解析总分: {total_score}")
                break
        
        if total_score == 0:
            print("❌ 未找到总分标签，尝试从各题得分中累加计算...")
            # 尝试从各题得分中累加
            score_matches = re.findall(r'得分[：:]?\s*(\d+)/\d+分', result_text)
            if score_matches:
                total_score = sum(int(score) for score in score_matches)
                print(f"✅ 通过累加各题得分计算总分: {total_score}")
            else:
                print("❌ 无法解析总分，总分为0")
        
        print(f"🎯 主观题阅卷完成，总分: {total_score}")
        
        return {
            '_total_score': total_score,
            '_full_report': result_text
        }
        
    except Exception as e:
        print(f"❌ 主观题评分失败: {e}")
        return {
            '_total_score': 0,
            '_full_report': f"评分失败: {str(e)}"
        }

def generate_subjective_report_direct(student, subjective_results, student_name, student_id):
    """
    生成主观题报告（直接处理版本）
    
    参数:
        student: 学生信息对象
        subjective_results: 主观题评分结果
        student_name: 学生姓名
        student_id: 学生学号
    
    返回:
        str: 报告文件路径，失败时返回None
    """
    try:
        print(f"🔍 生成报告调试信息:")
        print(f"👤 学生信息: {student_name} ({student_id})")
        print(f"📊 主观题结果: {subjective_results}")
        
        # 创建报告目录
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        print(f"📁 报告目录: {reports_dir}")
        
        # 生成报告文件名
        safe_name = "".join(c for c in student_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_id = "".join(c for c in student_id if c.isalnum() or c in (' ', '-', '_')).rstrip()
        report_filename = f"{safe_id}+{safe_name}+主观题.txt"
        report_path = reports_dir / report_filename
        print(f"📄 报告文件名: {report_filename}")
        print(f"📍 报告完整路径: {report_path}")
        
        # 获取评分报告内容
        full_report = subjective_results.get('_full_report', '无评分报告')
        total_score = subjective_results.get('_total_score', 0)
        print(f"📊 总分: {total_score}")
        print(f"📄 报告内容长度: {len(full_report)} 字符")
        
        # 生成报告内容
        report_content = f"""主观题阅卷报告
==================

学生信息：
姓名：{student_name}
学号：{student_id}
评分时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

主观题总分：{total_score}分

详细评分：
{full_report}

==================
报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        # 写入报告文件
        print(f"💾 写入报告文件...")
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"✅ 主观题报告文件生成成功: {report_path}")
            
            # 验证文件是否真的被创建
            if report_path.exists():
                file_size = report_path.stat().st_size
                print(f"📏 报告文件大小: {file_size} 字节")
                return str(report_path)
            else:
                print(f"❌ 报告文件未能成功创建")
                return None
                
        except Exception as write_error:
            print(f"❌ 写入报告文件时出错: {write_error}")
            return None
        
    except Exception as e:
        print(f"❌ 生成主观题报告失败: {e}")
        return None