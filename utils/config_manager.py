#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import base64
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = None):
        if config_file is None:
             # Default to config/config.json relative to project root
            from utils.path_utils import get_project_root
            config_file = os.path.join(get_project_root(), "config", "config.json")
            
        self.config_file = config_file
        self.default_config = {
            "objective_answer_path": os.path.join("config", "answer_config", "answer_multiple.txt"),
            "subjective_answer_path": os.path.join("config", "answer_config", "subjective_answer.txt"),
            "api_key": "",
            "api_base_url": "https://api.siliconflow.cn/v1",
            "model_name": "Qwen/Qwen2-VL-72B-Instruct",
            "available_models": [
                "zai-org/GLM-4.6V",
                "Qwen/Qwen3-VL-8B-Instruct",
                "Qwen/Qwen3-VL-8B-Thinking",
                "Qwen/Qwen3-VL-32B-Instruct",
                "Qwen/Qwen3-VL-32B-Thinking",
                "Qwen/Qwen3-VL-30B-A3B-Instruct",
                "Qwen/Qwen3-VL-30B-A3B-Thinking",
                "Qwen/Qwen3-VL-235B-A22B-Instruct",
                "Qwen/Qwen3-VL-235B-A22B-Thinking"
            ],
            "auto_load_config": True,
            "enable_student_info": True,
            "objective_scoring_rule": "standard",
            "recognition": {
                "mode": "A",  # 识别模式：A(自然顺序) 或 B(列优先)
                "layout": "row",  # 题列布局：row(一行一题) 或 column(一列一题)
                "group_size": 5,    # 每张图片包含的题目数量（题组大小）
                "conf_thres": 0.75  # 检测置信度阈值（YOLO过滤）
            },
            "last_updated": ""
        }
        self.config = self.load_config()
    
    def _encrypt_string(self, text: str) -> str:
        """加密字符串"""
        if not text: return ""
        try:
            from cryptography.fernet import Fernet
            # 固定密钥用于配置文件加密（非硬件绑定）
            key = base64.urlsafe_b64encode(hashlib.sha256(b"MarkingSystem_Config_Key_2024").digest())
            f = Fernet(key)
            encrypted = f.encrypt(text.encode()).decode()
            return f"enc:{encrypted}"
        except ImportError:
            return "enc:" + base64.b64encode(text.encode()).decode()

    def _decrypt_string(self, text: str) -> str:
        """解密字符串"""
        if not text or not text.startswith("enc:"): return text
        payload = text[4:]
        try:
            from cryptography.fernet import Fernet
            key = base64.urlsafe_b64encode(hashlib.sha256(b"MarkingSystem_Config_Key_2024").digest())
            f = Fernet(key)
            return f.decrypt(payload.encode()).decode()
        except Exception:
             try:
                 return base64.b64decode(payload.encode()).decode()
             except:
                 return text

    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            config = None
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                # 尝试从资源路径加载（支持打包后的默认配置）
                from utils.path_utils import get_resource_path
                resource_config = get_resource_path(os.path.join("config", "config.json"))
                if os.path.exists(resource_config) and resource_config != self.config_file:
                    with open(resource_config, 'r', encoding='utf-8') as f:
                        config = json.load(f)
            
            if config:
                # 解密API Key
                if "api_key" in config and isinstance(config["api_key"], str):
                    if config["api_key"].startswith("enc:"):
                        config["api_key"] = self._decrypt_string(config["api_key"])
                    
                    # 检查是否为旧版本残留的试用Key，如果是则清除
                    if config["api_key"] == "sk-sqtwlhrpkekvkfeecxlqtnsujkktthereerunvrtxqkjeabi":
                        config["api_key"] = ""

                # 合并默认配置，确保所有必要的键都存在
                for key, value in self.default_config.items():
                    if key not in config:
                        config[key] = value
                
                default_models = self.default_config.get("available_models", [])
                saved_models = config.get("available_models") if isinstance(config.get("available_models"), list) else []
                merged_models = []
                for m in saved_models + default_models:
                    if m and m not in merged_models:
                        merged_models.append(m)
                model_name = config.get("model_name")
                if model_name and model_name not in merged_models:
                    merged_models.append(model_name)
                config["available_models"] = merged_models
                
                # 如果是首次从资源加载（用户路径不存在），保存到用户路径
                if not os.path.exists(self.config_file):
                    self.save_config(config)

                return config
            else:
                # 如果配置文件不存在，创建默认配置
                self.save_config(self.default_config)
                return self.default_config.copy()
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return self.default_config.copy()
    
    def save_config(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """保存配置文件"""
        try:
            if config is None:
                config = self.config
            
            # 创建副本以避免修改内存中的配置（加密API Key）
            config_to_save = config.copy()
            if "api_key" in config_to_save and config_to_save["api_key"]:
                if not config_to_save["api_key"].startswith("enc:"):
                    config_to_save["api_key"] = self._encrypt_string(config_to_save["api_key"])
            
            # 更新最后修改时间
            config_to_save["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 确保目录存在
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, ensure_ascii=False, indent=4)
            
            self.config = config
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> bool:
        """设置配置项"""
        self.config[key] = value
        return self.save_config()
    
    def update(self, updates: Dict[str, Any]) -> bool:
        """批量更新配置"""
        try:
            self.config.update(updates)
            # 立即保存配置到文件
            return self.save_config()
        except Exception as e:
            print(f"更新配置失败: {e}")
            return False

    # 识别配置相关接口
    def get_recognition_config(self) -> Dict[str, Any]:
        """获取识别配置字典"""
        rec = self.config.get("recognition")
        if not isinstance(rec, dict):
            # 回退到默认
            rec = self.default_config["recognition"].copy()
            self.config["recognition"] = rec
        # 兜底mode
        if "mode" not in rec:
            rec["mode"] = self.default_config["recognition"]["mode"]
        # 兜底layout
        if "layout" not in rec:
            rec["layout"] = self.default_config["recognition"]["layout"]
        # 兜底group_size
        if "group_size" not in rec:
            rec["group_size"] = self.default_config["recognition"]["group_size"]
        return rec

    def get_recognition_mode(self) -> str:
        """获取识别模式(A/B)"""
        mode = self.get_recognition_config().get("mode", "A")
        mode = str(mode).upper().strip()
        return "B" if mode == "B" else "A"

    def set_recognition_mode(self, mode: str) -> bool:
        """设置识别模式(A/B)并保存"""
        m = str(mode).upper().strip()
        if m not in ("A", "B"):
            m = "A"
        # 确保recognition字典存在
        rec = self.config.get("recognition")
        if not isinstance(rec, dict):
            rec = {}
            self.config["recognition"] = rec
        rec["mode"] = m
        return self.save_config()

    def get_objective_scoring_rule(self) -> str:
        rule = str(self.config.get("objective_scoring_rule", "standard")).strip().lower()
        return "partial_penalty" if rule == "partial_penalty" else "standard"

    def set_objective_scoring_rule(self, rule: str) -> bool:
        r = str(rule).strip().lower()
        if r not in ("standard", "partial_penalty"):
            r = "standard"
        self.config["objective_scoring_rule"] = r
        return self.save_config()

    def get_recognition_layout(self) -> str:
        """获取题列布局(row/column)"""
        layout = str(self.get_recognition_config().get("layout", "row")).lower().strip()
        return "column" if layout == "column" else "row"

    def set_recognition_layout(self, layout: str) -> bool:
        """设置题列布局(row/column)并保存"""
        l = str(layout).lower().strip()
        if l not in ("row", "column"):
            l = "row"
        rec = self.config.get("recognition")
        if not isinstance(rec, dict):
            rec = {}
            self.config["recognition"] = rec
        rec["layout"] = l
        return self.save_config()

    def get_recognition_group_size(self) -> int:
        """获取每张图片的题组数量（每图题数）"""
        try:
            size = int(self.get_recognition_config().get("group_size", 5))
        except Exception:
            size = 5
        if size < 1:
            size = 1
        return size

    def set_recognition_group_size(self, size: int) -> bool:
        """设置题组数量并保存（最小为1）"""
        try:
            s = int(size)
        except Exception:
            s = 5
        if s < 1:
            s = 1
        rec = self.config.get("recognition")
        if not isinstance(rec, dict):
            rec = {}
            self.config["recognition"] = rec
        rec["group_size"] = s
        return self.save_config()

    def get_recognition_conf_thres(self) -> float:
        """获取检测置信度阈值"""
        rec = self.get_recognition_config()
        value = rec.get("conf_thres", 0.75)
        try:
            v = float(value)
        except Exception:
            v = 0.75
        if v < 0.01:
            v = 0.01
        if v > 0.99:
            v = 0.99
        return v

    def set_recognition_conf_thres(self, value: float) -> bool:
        """设置检测置信度阈值并保存"""
        try:
            v = float(value)
        except Exception:
            v = 0.75
        if v < 0.01:
            v = 0.01
        if v > 0.99:
            v = 0.99
        rec = self.config.get("recognition")
        if not isinstance(rec, dict):
            rec = {}
            self.config["recognition"] = rec
        rec["conf_thres"] = v
        return self.save_config()
    
    def get_objective_answer_path(self) -> str:
        """获取客观题答案路径"""
        from utils.path_utils import get_config_file_path
        path = self.get("objective_answer_path", "answer_multiple.txt")
        # 如果是相对路径，转换为绝对路径
        if not os.path.isabs(path):
            path = get_config_file_path(os.path.basename(path))
        return path
    
    def get_subjective_answer_path(self) -> str:
        """获取主观题答案路径"""
        from utils.path_utils import get_config_file_path
        path = self.get("subjective_answer_path", "test_subjective_answer.txt")
        # 如果是相对路径，转换为绝对路径
        if not os.path.isabs(path):
            path = get_config_file_path(os.path.basename(path))
        return path
    
    def get_api_key(self) -> str:
        """获取API密钥 (自动处理试用期内置密钥)"""
        user_key = self.get("api_key", "")
        # 如果用户配置了有效的Key（且不是默认提示文本），直接使用
        # 增加长度校验，防止用户配置了截断的无效Key
        if user_key and user_key.strip() and user_key != "your_api_key_here" and len(user_key) > 20:
            print("Using User API Key")
            return user_key
        
        # 检查是否处于试用期，如果是则返回内置Key
        try:
            from utils.activation import ActivationManager
            am = ActivationManager()
            # 只有在未激活且试用期有效的情况下才使用内置Key
            if not am.is_activated():
                is_valid, _, _ = am.check_trial_status()
                if is_valid:
                    print("Using Trial Built-in API Key")
                    return "sk-sqtwlhrpkekvkfeecxlqtnsujkktthereerunvrtxqkjeabi"
        except Exception as e:
            print(f"检查试用期Key失败: {e}")
        
        return ""
    
    def get_api_config(self) -> Dict[str, str]:
        """获取API配置"""
        return {
            "api_key": self.get_api_key(),
            "api_base_url": self.get("api_base_url", "https://api.siliconflow.cn/v1"),
            "model_name": self.get("model_name", "Qwen/Qwen2-VL-72B-Instruct")
        }
    
    def is_auto_load_enabled(self) -> bool:
        """是否启用自动加载配置"""
        return self.get("auto_load_config", True)
    
    def is_student_info_enabled(self) -> bool:
        """是否启用学生信息识别"""
        return self.get("enable_student_info", True)
    
    def validate_paths(self) -> Dict[str, bool]:
        """验证文件路径是否存在"""
        return {
            "objective_answer": os.path.exists(self.get_objective_answer_path()),
            "subjective_answer": os.path.exists(self.get_subjective_answer_path())
        }
    
    def validate_api_key(self) -> bool:
        """验证API密钥是否配置"""
        api_key = self.get_api_key()
        return bool(api_key and api_key.strip() and api_key != "your_api_key_here")
    
    def get_status(self) -> Dict[str, Any]:
        """获取配置状态"""
        path_status = self.validate_paths()
        return {
            "config_file_exists": os.path.exists(self.config_file),
            "auto_load_enabled": self.is_auto_load_enabled(),
            "student_info_enabled": self.is_student_info_enabled(),
            "objective_answer_exists": path_status["objective_answer"],
            "subjective_answer_exists": path_status["subjective_answer"],
            "api_key_configured": self.validate_api_key(),
            "last_updated": self.get("last_updated", "未知")
        }

# 全局配置管理器实例
config_manager = ConfigManager()

if __name__ == "__main__":
    # 测试配置管理器
    print("配置管理器测试")
    print("=" * 50)
    
    # 显示当前配置
    print("当前配置:")
    for key, value in config_manager.config.items():
        if key == "api_key" and value:
            # 隐藏API密钥的大部分内容
            masked_value = value[:6] + "***" + value[-6:] if len(value) > 12 else "*" * len(value)
            print(f"  {key}: {masked_value}")
        else:
            print(f"  {key}: {value}")
    
    print("\n配置状态:")
    status = config_manager.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
