import sys
import uuid
import hashlib
import socket
import platform
import json
import requests
import hmac
import base64
import time
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

from PySide6.QtCore import QSettings

# 服务器配置
SERVER_URL = "http://8.148.238.73:5000/api"  # 替换为您的服务器IP和端口


class HardwareInfo:
    """硬件信息收集类"""

    @staticmethod
    def get_cpu_info() -> str:
        """获取CPU信息"""
        try:
            if platform.system() == "Windows":
                import wmi
                c = wmi.WMI()
                for cpu in c.Win32_Processor():
                    return f"{cpu.Name}-{cpu.ProcessorId}"
            elif platform.system() == "Linux":
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if line.startswith("model name") or line.startswith("physical id") or line.startswith("serial"):
                            return line.strip()
            elif platform.system() == "Darwin":  # macOS
                import subprocess
                cmd = "sysctl -n machdep.cpu.brand_string"
                return subprocess.check_output(cmd, shell=True).decode().strip()
        except Exception as e:
            print(f"获取CPU信息失败: {e}")
        return platform.processor()

    @staticmethod
    def get_mac_address() -> str:
        """获取MAC地址"""
        mac = uuid.getnode()
        return ':'.join(['{:02x}'.format((mac >> elements) & 0xff) for elements in range(0, 8 * 6, 8)][::-1])

    @staticmethod
    def get_disk_serial() -> str:
        """获取硬盘序列号"""
        try:
            if platform.system() == "Windows":
                import wmi
                c = wmi.WMI()
                for disk in c.Win32_DiskDrive():
                    if disk.SerialNumber:
                        return disk.SerialNumber
            elif platform.system() == "Linux":
                import subprocess
                cmd = "lsblk -o NAME,SERIAL | grep -v NAME | head -n1"
                return subprocess.check_output(cmd, shell=True).decode().strip()
        except Exception as e:
            print(f"获取硬盘序列号失败: {e}")
        return ""

    @staticmethod
    def get_motherboard_serial() -> str:
        """获取主板序列号"""
        try:
            if platform.system() == "Windows":
                import wmi
                c = wmi.WMI()
                for board in c.Win32_BaseBoard():
                    if board.SerialNumber:
                        return board.SerialNumber
            elif platform.system() == "Linux":
                import subprocess
                cmd = "dmidecode -t 2 | grep Serial"
                return subprocess.check_output(cmd, shell=True).decode().strip()
        except Exception as e:
            print(f"获取主板序列号失败: {e}")
        return ""

    @staticmethod
    def get_hardware_id() -> str:
        """生成硬件ID"""
        # 收集硬件信息
        cpu_info = HardwareInfo.get_cpu_info()
        mac_address = HardwareInfo.get_mac_address()
        disk_serial = HardwareInfo.get_disk_serial()
        motherboard_serial = HardwareInfo.get_motherboard_serial()
        hostname = socket.gethostname()

        # 组合信息并哈希
        combined = f"{cpu_info}|{mac_address}|{disk_serial}|{motherboard_serial}|{hostname}"
        # print(combined) # Debug
        return hashlib.sha256(combined.encode()).hexdigest()


class ActivationManager:
    """激活管理类"""
    TRIAL_DAYS = 1
    
    def __init__(self):
        self.settings = QSettings("MarkingSystem", "Activation")
        from utils.path_utils import get_project_root
        self.config_dir = Path(get_project_root()) / "config"
        self.activation_file = self.config_dir / "activation.dat"
        self.trial_file = self.config_dir / "trial.dat"
        
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)

    def _get_encryption_key(self) -> bytes:
        """基于硬件ID生成加密密钥"""
        hardware_id = HardwareInfo.get_hardware_id()
        # 使用硬件ID和固定密钥生成加密密钥
        key_material = hashlib.sha256(f"{hardware_id}:MarkingSystem_EncryptKey_2024".encode()).digest()
        return base64.urlsafe_b64encode(key_material[:32])  # AES需要32字节密钥

    def _encrypt_data(self, data: str) -> bytes:
        """加密数据"""
        try:
            from cryptography.fernet import Fernet
            key = self._get_encryption_key()
            fernet = Fernet(key)
            return fernet.encrypt(data.encode())
        except ImportError:
            # 如果没有cryptography库，使用简单的base64编码（不安全，但可用）
            # print("警告: 未安装cryptography库，使用简单编码")
            return base64.b64encode(data.encode())

    def _decrypt_data(self, encrypted_data: bytes) -> str:
        """解密数据"""
        try:
            from cryptography.fernet import Fernet
            key = self._get_encryption_key()
            fernet = Fernet(key)
            return fernet.decrypt(encrypted_data).decode()
        except ImportError:
            # 如果没有cryptography库，使用简单的base64解码
            return base64.b64decode(encrypted_data).decode()
        except Exception as e:
            print(f"解密失败: {e}")
            raise

    def is_activated(self) -> bool:
        """检查软件是否已激活"""
        # 只检查本地激活文件，不进行在线验证
        return self._check_local_activation()

    def _check_local_activation(self) -> bool:
        """检查本地激活文件"""
        if not self.activation_file.exists():
            return False

        try:
            # 读取加密的激活文件
            with open(self.activation_file, "rb") as f:
                encrypted_data = f.read()

            # 解密数据
            decrypted_json = self._decrypt_data(encrypted_data)
            data = json.loads(decrypted_json)

            # 验证激活数据
            stored_hardware_id = data.get("hardware_id", "")
            activation_code = data.get("activation_code", "")
            signature = data.get("signature", "")

            # 验证硬件ID是否匹配
            current_hardware_id = HardwareInfo.get_hardware_id()
            if stored_hardware_id != current_hardware_id:
                print(f"硬件ID不匹配: 存储的={stored_hardware_id[:16]}..., 当前的={current_hardware_id[:16]}...")
                return False

            # 验证签名
            expected_signature = self._generate_signature(current_hardware_id, activation_code)
            signature_valid = hmac.compare_digest(signature, expected_signature)
            
            if not signature_valid:
                print("签名验证失败")
                return False
                
            # print("本地激活验证通过")
            return True

        except Exception as e:
            print(f"检查本地激活失败: {e}")
            return False

    def _verify_online(self) -> bool:
        """在线验证激活状态（仅在激活时使用）"""
        try:
            hardware_id = HardwareInfo.get_hardware_id()
            response = requests.post(
                f"{SERVER_URL}/verify",
                json={"hardware_id": hardware_id},
                timeout=5  # 5秒超时
            )

            if response.status_code == 200:
                return response.json().get("is_activated", False)
            return False
        except Exception as e:
            print(f"在线验证失败: {e}")
            raise

    def activate(self, activation_code: str) -> Tuple[bool, str]:
        """激活软件"""
        hardware_id = HardwareInfo.get_hardware_id()

        try:
            # 尝试在线激活
            response = requests.post(
                f"{SERVER_URL}/activate",
                json={
                    "activation_code": activation_code,
                    "hardware_id": hardware_id
                },
                timeout=10
            )

            if response.status_code == 201 or response.status_code == 200:
                # 激活成功，保存加密的激活信息
                self._save_activation_data(hardware_id, activation_code)
                return True, "激活成功！"
            else:
                error_msg = response.json().get("message", "激活失败，请检查激活码是否有效。")
                return False, error_msg

        except requests.RequestException as e:
            print(f"在线激活失败: {e}")
            # 尝试离线激活（简单实现，实际应用中应该更安全）
            if self._offline_activate(activation_code, hardware_id):
                return True, "离线激活成功！"
            return False, "激活失败，无法连接到服务器。"

    def _offline_activate(self, activation_code: str, hardware_id: str) -> bool:
        """离线激活（简单实现）"""
        # 这里应该有更复杂的离线激活逻辑，例如验证预生成的激活码列表
        # 简单起见，这里只做基本验证
        # 这里假设长度16位即为合法，实际应有更强的本地校验算法
        if len(activation_code) >= 16:
            self._save_activation_data(hardware_id, activation_code)
            return True
        return False

    def _save_activation_data(self, hardware_id: str, activation_code: str) -> None:
        """保存加密的激活数据"""
        signature = self._generate_signature(hardware_id, activation_code)

        activation_data = {
            "hardware_id": hardware_id,
            "activation_code": activation_code,
            "activation_time": int(time.time()),
            "signature": signature,
            "version": "1.0"  # 添加版本信息
        }

        # 将数据转换为JSON字符串
        json_data = json.dumps(activation_data, separators=(',', ':'))
        
        # 加密数据
        encrypted_data = self._encrypt_data(json_data)

        # 保存加密的数据
        with open(self.activation_file, "wb") as f:
            f.write(encrypted_data)

        print("激活数据已加密保存")

    def _generate_signature(self, hardware_id: str, activation_code: str) -> str:
        """生成签名"""
        # 在实际应用中，应该使用更安全的方法，可能包括公钥加密
        key = "MarkingSystem_SecretKey_2024"  # 应该是一个安全的密钥
        message = f"{hardware_id}:{activation_code}:MarkingSystem"
        signature = hmac.new(key.encode(), message.encode(), hashlib.sha256).hexdigest()
        return signature

    def clear_activation(self) -> bool:
        """清除激活数据（用于测试或重置）"""
        try:
            if self.activation_file.exists():
                self.activation_file.unlink()
                print("激活数据已清除")
                return True
        except Exception as e:
            print(f"清除激活数据失败: {e}")
        return False

    # === 试用期管理逻辑 ===

    def check_trial_status(self) -> Tuple[bool, str, int]:
        """
        检查试用期状态
        返回: (是否允许进入, 提示信息, 剩余天数)
        """
        # 1. 如果已激活，直接通过
        if self.is_activated():
            return True, "已激活专业版", 999

        current_time = time.time()
        
        # 2. 读取试用文件
        if not self.trial_file.exists():
            # 首次运行，创建试用记录
            trial_data = {
                "start_time": current_time,
                "last_run_time": current_time,
                "hardware_id": HardwareInfo.get_hardware_id()
            }
            self._save_trial_data(trial_data)
            return True, f"欢迎试用！您还有 {self.TRIAL_DAYS} 天试用期。", self.TRIAL_DAYS

        try:
            trial_data = self._load_trial_data()
            if not trial_data:
                return False, "试用记录损坏", 0
                
            # 检查硬件ID
            if trial_data.get("hardware_id") != HardwareInfo.get_hardware_id():
                return False, "试用记录与当前设备不匹配", 0
                
            start_time = trial_data.get("start_time", current_time)
            last_run_time = trial_data.get("last_run_time", current_time)
            
            # 检查时间倒流
            if current_time < last_run_time:
                return False, "系统时间异常，请校准时间", 0
                
            # 更新最后运行时间
            trial_data["last_run_time"] = current_time
            self._save_trial_data(trial_data)
            
            # 计算剩余时间
            elapsed_days = (current_time - start_time) / (24 * 3600)
            remaining_days = self.TRIAL_DAYS - elapsed_days
            
            if remaining_days > 0:
                days_int = int(remaining_days) + 1
                return True, f"试用期剩余 {days_int} 天", days_int
            else:
                return False, "试用期已结束，请购买激活码", 0
                
        except Exception as e:
            print(f"试用检查失败: {e}")
            return False, "试用检查出错", 0

    def _save_trial_data(self, data: Dict):
        """保存加密的试用数据"""
        json_data = json.dumps(data)
        encrypted = self._encrypt_data(json_data)
        with open(self.trial_file, "wb") as f:
            f.write(encrypted)

    def _load_trial_data(self) -> Optional[Dict]:
        """加载试用数据"""
        try:
            with open(self.trial_file, "rb") as f:
                encrypted = f.read()
            decrypted = self._decrypt_data(encrypted)
            return json.loads(decrypted)
        except Exception:
            return None
