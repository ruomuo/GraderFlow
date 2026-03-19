from flask import Flask, request, jsonify
import os
import requests
from urllib.parse import urlparse
import tempfile
import uuid
import base64
from core.omr.pipeline import AnswerRecognizer

app = Flask(__name__)

# 初始化答题卡识别器
recognizer = AnswerRecognizer()

@app.route('/recognize', methods=['POST'])
def recognize_answer_card():
    """
    答题卡识别接口
    
    请求参数:
        image_url (str): 答题卡图片的URL地址
    
    返回:
        JSON格式的识别结果
    """
    try:
        # 获取请求参数
        data = request.get_json()
        if not data or 'image_url' not in data:
            return jsonify({
                'success': False,
                'error': '缺少image_url参数'
            }), 400
        
        image_url = data['image_url']
        
        # 验证URL格式
        try:
            parsed_url = urlparse(image_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError("无效的URL格式")
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'无效的URL格式: {str(e)}'
            }), 400
        
        # 下载图片到临时文件
        temp_dir = tempfile.gettempdir()
        temp_filename = f"answer_card_{uuid.uuid4().hex}.jpg"
        temp_filepath = os.path.join(temp_dir, temp_filename)
        
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            with open(temp_filepath, 'wb') as f:
                f.write(response.content)
        except requests.RequestException as e:
            return jsonify({
                'success': False,
                'error': f'下载图片失败: {str(e)}'
            }), 400
        
        try:
            # 识别答题卡
            raw_result = recognizer.recognize(temp_filepath)
            
            # 格式化结果
            formatted_result = recognizer.format_result(raw_result)
            
            return jsonify({
                'success': True,
                'data': formatted_result
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'识别失败: {str(e)}'
            }), 500
        
        finally:
            # 清理临时文件
            if os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                except:
                    pass
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'服务器内部错误: {str(e)}'
        }), 500

@app.route('/recognize_base64', methods=['POST'])
def recognize_answer_card_base64():
    """
    答题卡识别接口 - 支持Base64图片数据
    
    请求参数:
        image (str): Base64编码的图片数据
    
    返回:
        JSON格式的识别结果
    """
    try:
        # 获取请求参数
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({
                'success': False,
                'error': '缺少image参数'
            }), 400
        
        image_base64 = data['image']
        
        # 解码Base64图片数据
        try:
            image_data = base64.b64decode(image_base64)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Base64解码失败: {str(e)}'
            }), 400
        
        # 保存到临时文件
        temp_dir = tempfile.gettempdir()
        temp_filename = f"answer_card_{uuid.uuid4().hex}.jpg"
        temp_filepath = os.path.join(temp_dir, temp_filename)
        
        try:
            with open(temp_filepath, 'wb') as f:
                f.write(image_data)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'保存图片失败: {str(e)}'
            }), 400
        
        try:
            # 识别答题卡
            raw_result = recognizer.recognize(temp_filepath)
            
            # 格式化结果
            formatted_result = recognizer.format_result(raw_result)
            
            return jsonify({
                'success': True,
                'data': formatted_result
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'识别失败: {str(e)}'
            }), 500
        
        finally:
            # 清理临时文件
            if os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                except:
                    pass
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'服务器内部错误: {str(e)}'
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """
    健康检查接口
    """
    return jsonify({
        'status': 'healthy',
        'service': 'answer_recognition_api'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)