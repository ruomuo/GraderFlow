from PIL import Image
import io
import base64
import re
import json
import time
from openai import OpenAI, APIConnectionError, RateLimitError, APIStatusError, AuthenticationError, APITimeoutError
from utils.config_manager import config_manager

def convert_image_to_webp_base64(input_image_path):
    try:
        # 检查输入路径是否有效
        if not input_image_path or not isinstance(input_image_path, str):
            print(f"Error: Invalid image path: {input_image_path}")
            return None
            
        # 检查文件是否存在
        import os
        if not os.path.exists(input_image_path):
            print(f"Error: Image file does not exist: {input_image_path}")
            return None
            
        with Image.open(input_image_path) as img:
            byte_arr = io.BytesIO()
            img.save(byte_arr, format='webp')
            byte_arr = byte_arr.getvalue()
            base64_str = base64.b64encode(byte_arr).decode('utf-8')
            return base64_str
    except IOError as e:
        print(f"Error: Unable to open or convert the image {input_image_path}: {e}")
        return None
    except Exception as e:
        print(f"Error: Unexpected error when processing image {input_image_path}: {e}")
        return None

def get_info_json(api_key,input_image_path):
    try:
        base_url = config_manager.get("api_base_url", "https://api.siliconflow.cn/v1")
        if "/chat/completions" in base_url:
            base_url = base_url.split("/chat/completions")[0]
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )

        base64_image = convert_image_to_webp_base64(input_image_path)
        if not base64_image:
            print("❌ 图片转换失败")
            return "", ""

        stream_start_time = time.time()
        response = client.chat.completions.create(
            model=config_manager.get("model_name"),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "请识别图片中的考生姓名和考号信息。考号也可能叫准考证号或学号。如果图片中没有显示姓名或考号信息，请返回空值。请用JSON格式返回结果，格式如下：{\"姓名\": \"姓名内容或空字符串\", \"考号\": \"考号内容或空字符串\"}"
                        }
                    ]
                }],
            stream=True
        )
        complete_message = ""
        for chunk in response:
            try:
                choices = getattr(chunk, "choices", None)
                if not choices:
                    continue
                delta = choices[0].delta
                chunk_message = getattr(delta, "content", None)
                if chunk_message:
                    complete_message += chunk_message
            except Exception:
                continue
        stream_elapsed = time.time() - stream_start_time
        print(f"⏱️ 提取姓名考号（流式）耗时: {stream_elapsed:.3f}s")
        print(f"🧾 模型响应（流式）: {repr(complete_message)}")
        if complete_message:
            stu_name, stu_number = parse_str(complete_message)
            return stu_name, stu_number

        non_stream_start_time = time.time()
        response = client.chat.completions.create(
            model=config_manager.get("model_name"),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "请识别图片中的考生姓名和考号信息。考号也可能叫准考证号或学号。如果图片中没有显示姓名或考号信息，请返回空值。请用JSON格式返回结果，格式如下：{\"姓名\": \"姓名内容或空字符串\", \"考号\": \"考号内容或空字符串\"}"
                        }
                    ]
                }],
            stream=False
        )
        non_stream_elapsed = time.time() - non_stream_start_time
        message = response.choices[0].message.content if response and response.choices else ""
        print(f"⏱️ 提取姓名考号（非流式）耗时: {non_stream_elapsed:.3f}s")
        print(f"🧾 模型响应（非流式）: {repr(message)}")
        stu_name, stu_number = parse_str(message)
        return stu_name, stu_number
    except APIConnectionError as e:
        print(f"❌ API连接错误: {str(e)}")
        print("🔍 网络连接问题，请检查:")
        print("  1. 网络连接是否正常")
        print("  2. API基础URL是否正确")
        print("  3. 防火墙或代理设置")
        return "", ""
    except AuthenticationError as e:
        print(f"❌ API认证失败: {str(e)}")
        print("🔍 请检查API密钥是否正确，或试用期已过")
        print("🔍 如需继续使用，请前往硅基流动官网(https://cloud.siliconflow.cn)申请API Key")
        return "", ""
    except RateLimitError as e:
        print(f"❌ API请求限流: {str(e)}")
        print("🔍 请检查API配额或调用频率")
        return "", ""
    except APITimeoutError as e:
        print(f"❌ API请求超时: {str(e)}")
        print("🔍 服务器响应过慢，请稍后重试")
        return "", ""
    except APIStatusError as e:
        print(f"❌ API状态错误 {e.status_code}: {e.message}")
        return "", ""
    except Exception as e:
        print(f"❌ API调用异常: {str(e)}")
        if "Connection error" in str(e) or "ConnectionError" in str(e):
            print("🔍 网络连接问题，请检查:")
            print("  1. 网络连接是否正常")
            print("  2. API基础URL是否正确")
            print("  3. API密钥是否有效")
            print("  4. 防火墙或代理设置")
        return "", ""


def parse_str(complete_message):
    # 步骤 1：清洗非 JSON 内容，正确处理 Markdown 代码块格式和特殊标记
    clean_json = complete_message.strip()
    
    # 移除特殊前缀标记（如 <|begin_of_box|>、<|end_of_box|> 等）
    import re
    clean_json = re.sub(r'<\|[^|]*\|>', '', clean_json)
    
    # 移除 Markdown 代码块标记 - 更彻底的清洗
    if clean_json.startswith("```json"):
        clean_json = clean_json[7:]  # 移除开头的 ```json
    elif clean_json.startswith("```"):
        clean_json = clean_json[3:]  # 移除开头的 ```
    
    clean_json = clean_json.strip()
    
    # 查找JSON结束位置 - 寻找第一个完整的JSON对象
    try:
        # 尝试找到JSON的结束位置
        brace_count = 0
        json_end = -1
        in_string = False
        escape_next = False
        
        for i, char in enumerate(clean_json):
            if escape_next:
                escape_next = False
                continue
                
            if char == '\\':
                escape_next = True
                continue
                
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
                
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break
        
        if json_end > 0:
            clean_json = clean_json[:json_end]
    except:
        # 如果解析失败，尝试其他方法
        pass
    
    # 移除可能残留的标记
    while clean_json.endswith("```") or clean_json.endswith("\n```"):
        if clean_json.endswith("\n```"):
            clean_json = clean_json[:-4]
        elif clean_json.endswith("```"):
            clean_json = clean_json[:-3]
        clean_json = clean_json.strip()

    # 步骤 2：解析 JSON 字符串
    try:
        data = json.loads(clean_json)
        stu_name = re.sub(r'\s+', '', str(data.get("姓名", "")))  # 删除所有空格
        stu_number = re.sub(r'\s+', '', str(data.get("考号", "")))  # 包括数字间空格
    except json.JSONDecodeError as e:
        print(f"JSON 解析失败: {e}")
        print(f"原始内容: {repr(complete_message)}")  # 显示原始内容
        print(f"清洗后的JSON内容: {repr(clean_json)}")  # 添加调试信息
        
        # 尝试更激进的清洗方法
        try:
            # 查找JSON模式的内容
            json_pattern = r'\{[^{}]*"姓名"[^{}]*"考号"[^{}]*\}'
            match = re.search(json_pattern, complete_message)
            if match:
                json_str = match.group(0)
                print(f"通过正则表达式提取的JSON: {repr(json_str)}")
                data = json.loads(json_str)
                stu_name = re.sub(r'\s+', '', str(data.get("姓名", "")))
                stu_number = re.sub(r'\s+', '', str(data.get("考号", "")))
                print(f"✅ 正则表达式解析成功: 姓名={stu_name}, 考号={stu_number}")
                return stu_name, stu_number
        except Exception as fallback_e:
            print(f"正则表达式解析也失败: {fallback_e}")
        
        return "", ""
    except KeyError as e:
        print(f"键不存在: {e}")
        return "", ""

    # 步骤 3：验证存储结果
    if stu_name or stu_number:
        print(f"考生姓名：{stu_name}")
        print(f"考试编号：{stu_number}")
    else:
        print("未检测到姓名和考号信息")
    return stu_name, stu_number


if __name__ == "__main__":
    API_KEY = "sk-seqcmucdylclohwcmaumhemuleouakukdtwfmsqlnnpaaprh"
    get_info_json(API_KEY, r"E:\code_space\code_python\MarkingSystem\test_img\answer_104.jpg")
