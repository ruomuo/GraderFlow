import os
import base64
from typing import Generator, List, Dict, Any, Tuple
from openai import OpenAI, APIConnectionError, RateLimitError, APIStatusError, AuthenticationError, APITimeoutError
from utils.config_manager import config_manager

class LLMAgent:
    """智能助手代理类"""
    
    def __init__(self):
        self.api_key = config_manager.get_api_key()
        self.base_url = config_manager.get("api_base_url")
        self.model_name = config_manager.get("model_name")
        self.client = None
        
        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            
        self.system_prompt = self._build_system_prompt()
        self.history = [{"role": "system", "content": self.system_prompt}]

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return """你是一个智能阅卷系统的AI助手。你的主要任务是协助用户配置客观题和主观题的答案。

请严格遵循以下输出格式规则：

1. **客观题配置**：
   当用户提供客观题答案时，请输出一个代码块，标记语言为 `objective`。
   内容格式为每行：`题号:答案:分值:选项个数`
   - 答案支持单选(A)或多选(AB)。
   - 默认分值若未指定，假设为1.0。
   - 默认选项个数若未指定，假设为4。
   - **重要规则**：如果用户提供的输入中包含多组题目（如“单选题1-20，多选题1-5”），且后续组的题号从1重新开始，你需要自动修正题号，使其在整体上保持连续。例如，若单选题结束于20，则多选题第1题应重编号为21，以此类推。
   
   示例：
   ```objective
   1:A:2.0:4
   2:B:2.0:4
   3:AB:3.0:4
   ```

2. **主观题配置**：
   当用户提供主观题答案时，请输出一个代码块，标记语言为 `subjective`。
   格式要求：
   - 题头：`X题（Y分）`
   - 采分点：`内容(+分值)`
   
   示例：
   ```subjective
   21题（10.0分）
   (1)叶绿体(+3)
   (2)氧气(+3)
   ```

3. **一般对话**：
   对于非配置类的请求，请用简洁、专业的中文回答。

请注意：
- 如果用户一次性提供了大量题目，请完整输出所有题目的配置。
- 如果信息不全（如未提供分值），请使用合理的默认值（客观题1分，主观题根据总分合理分配或标记为待定）。
"""

    def update_config(self):
        """更新配置（当用户在设置中修改了API Key后调用）"""
        self.api_key = config_manager.get_api_key()
        self.base_url = config_manager.get("api_base_url")
        self.model_name = config_manager.get("model_name")
        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )

    def _encode_image(self, image_path: str) -> str:
        """编码图片为base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def chat(self, message: str, image_path: str = None) -> Generator[str, None, None]:
        """与AI对话（流式），支持图片输入"""
        if not self.client:
            yield "错误：未配置API Key或试用期已过。请在系统设置中配置API Key，或前往硅基流动官网(https://cloud.siliconflow.cn)申请。"
            return

        user_content = []
        if message:
            user_content.append({"type": "text", "text": message})
        
        if image_path:
            try:
                base64_image = self._encode_image(image_path)
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                })
            except Exception as e:
                yield f"图片处理失败: {str(e)}"
                return

        self.history.append({"role": "user", "content": user_content})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=self.history,
                stream=True,
                temperature=0.3
            )
            
            collected_content = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    collected_content += content
                    yield content
            
            self.history.append({"role": "assistant", "content": collected_content})
            
        except APIConnectionError as e:
            error_msg = f"连接服务器失败。请检查网络连接、DNS设置或代理设置。\n详细信息: {str(e)}"
            yield f"\n发生错误: {error_msg}"
        except AuthenticationError as e:
            error_msg = f"身份验证失败。请检查API Key是否正确，或试用期已过。\n如需继续使用，请前往硅基流动官网(https://cloud.siliconflow.cn)申请API Key。\n详细信息: {str(e)}"
            yield f"\n发生错误: {error_msg}"
        except RateLimitError as e:
            error_msg = f"请求过于频繁或余额不足。\n详细信息: {str(e)}"
            yield f"\n发生错误: {error_msg}"
        except APITimeoutError as e:
            error_msg = f"请求超时。服务器响应过慢。\n详细信息: {str(e)}"
            yield f"\n发生错误: {error_msg}"
        except APIStatusError as e:
            error_msg = f"服务器返回错误状态码 {e.status_code}。\n详细信息: {e.message}"
            yield f"\n发生错误: {error_msg}"
        except Exception as e:
            yield f"\n发生错误: {str(e)}"
