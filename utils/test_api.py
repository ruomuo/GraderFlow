#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
答题卡识别API测试脚本
使用 answer_125.jpg 测试 Base64 接口
"""

import base64
import json
import requests
import os

def test_api():
    """测试答题卡识别API"""
    
    # API配置
    api_url = "http://localhost:5000/recognize_base64"
    
    # 获取项目根目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    image_path = os.path.join(project_root, "tests", "data", "answer_125.jpg")
    
    print("=" * 60)
    print("答题卡识别API测试")
    print("=" * 60)
    print(f"API地址: {api_url}")
    print(f"测试图片: {image_path}")
    
    # 检查图片文件是否存在
    if not os.path.exists(image_path):
        print(f"❌ 错误: 图片文件不存在 - {image_path}")
        return
    
    try:
        # 读取图片并转换为Base64
        print("\n📖 读取图片文件...")
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        print(f"✅ 图片大小: {len(image_data)} 字节")
        print(f"✅ Base64长度: {len(image_base64)} 字符")
        
        # 构造请求数据
        request_data = {
            "image": image_base64
        }
        
        # 发送API请求
        print("\n🚀 发送API请求...")
        response = requests.post(
            api_url,
            json=request_data,
            headers={'Content-Type': 'application/json'},
            timeout=60
        )
        
        print(f"✅ HTTP状态码: {response.status_code}")
        
        # 解析响应
        if response.status_code == 200:
            result = response.json()
            
            print("\n📊 识别结果:")
            print("=" * 40)
            
            if result.get('success'):
                data = result.get('data', {})
                
                # 基本信息
                print(f"检测方法: {data.get('detection_method', 'unknown')}")
                print(f"检测区域数: {data.get('detected_regions', 0)}")
                print(f"总题目数: {data.get('total_questions', 0)}")
                
                # 统计信息
                if 'summary' in data:
                    summary = data['summary']
                    print(f"\n📈 统计信息:")
                    print(f"  已填涂: {summary.get('filled_count', 0)} 题")
                    print(f"  未填涂: {summary.get('empty_count', 0)} 题")
                    print(f"  单选题: {summary.get('single_choice_count', 0)} 题")
                    print(f"  多选题: {summary.get('multiple_choice_count', 0)} 题")
                
                # 答案详情（显示前10题）
                answers = data.get('answers', [])
                if answers:
                    print(f"\n📝 答案详情 (前10题):")
                    for i, answer in enumerate(answers[:10]):
                        question_num = answer.get('question_number', i+1)
                        answer_text = answer.get('answer', '')
                        question_type = answer.get('question_type', 'single')
                        is_filled = answer.get('is_filled', False)
                        
                        status = "✅" if is_filled else "❌"
                        print(f"  题目 {question_num:2d} ({question_type}): {answer_text:8s} {status}")
                    
                    if len(answers) > 10:
                        print(f"  ... 还有 {len(answers) - 10} 题")
                
                print("\n✅ 测试成功!")
                
            else:
                error_msg = result.get('error', '未知错误')
                print(f"❌ API返回错误: {error_msg}")
        
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            try:
                error_data = response.json()
                print(f"错误信息: {error_data}")
            except:
                print(f"响应内容: {response.text}")
    
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
    except requests.exceptions.ConnectionError:
        print("❌ 连接错误，请确保API服务正在运行")
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api()