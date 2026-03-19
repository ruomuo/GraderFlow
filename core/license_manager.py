import os
import sys
import json
import time
import hashlib
import base64
import uuid
import platform
from datetime import datetime, timedelta

try:
    import wmi
except ImportError:
    wmi = None

class LicenseManager:
    """
    许可证管理器
    负责机器码生成、试用期管理、激活码校验
    """
    _instance = None
    
    # 简单的混淆密钥，实际生产环境应更复杂或使用非对称加密
    SECRET_KEY = "OMR_SYSTEM_2025_SECRET_KEY_SALT_!@#"
    LICENSE_FILE = "license.dat"
    TRIAL_DAYS = 3

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LicenseManager, cls).__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.app_root = self._get_app_root()
        self.license_path = os.path.join(self.app_root, "config", self.LICENSE_FILE)
        self.machine_id = self._get_machine_id()
        self.status = "unknown"  # unknown, trial, activated, expired, tampered
        self.remaining_days = 0
        self.message = ""
        
        # 确保 config 目录存在
        config_dir = os.path.dirname(self.license_path)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

    def _get_app_root(self):
        """获取应用根目录"""
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _get_machine_id(self):
        """获取机器唯一标识"""
        try:
            if sys.platform == 'win32' and wmi:
                c = wmi.WMI()
                # 尝试获取 CPU 序列号和主板序列号
                cpu = c.Win32_Processor()[0].ProcessorId.strip()
                board = c.Win32_BaseBoard()[0].SerialNumber.strip()
                raw_id = f"{cpu}_{board}"
            else:
                # 回退方案：使用 MAC 地址
                raw_id = str(uuid.getnode())
        except Exception:
            raw_id = str(uuid.getnode())
        
        # 返回哈希后的机器码（大写，取前16位方便输入）
        return hashlib.md5(raw_id.encode()).hexdigest().upper()[:16]

    def _generate_signature(self, data_dict):
        """生成数据签名防止篡改"""
        # 将字典排序并转为字符串
        sorted_str = json.dumps(data_dict, sort_keys=True)
        return hashlib.sha256((sorted_str + self.SECRET_KEY).encode()).hexdigest()

    def _load_license(self):
        """加载许可证文件"""
        if not os.path.exists(self.license_path):
            return None
            
        try:
            with open(self.license_path, 'rb') as f:
                encrypted_data = f.read()
                
            # 简单的 Base64 解码
            json_str = base64.b64decode(encrypted_data).decode('utf-8')
            data = json.loads(json_str)
            
            # 校验签名
            stored_sig = data.pop('signature', '')
            current_sig = self._generate_signature(data)
            
            if stored_sig != current_sig:
                return {'status': 'tampered'}
                
            return data
        except Exception:
            return {'status': 'corrupted'}

    def _save_license(self, data):
        """保存许可证文件"""
        # 添加签名
        data['signature'] = self._generate_signature(data)
        
        # 编码并写入
        json_str = json.dumps(data)
        encrypted_data = base64.b64encode(json_str.encode('utf-8'))
        
        with open(self.license_path, 'wb') as f:
            f.write(encrypted_data)

    def check_license(self):
        """
        检查当前许可证状态
        返回: (is_valid, message)
        """
        data = self._load_license()
        current_time = time.time()
        
        # 情况1: 首次运行，没有许可证文件
        if data is None:
            # 初始化试用
            data = {
                'machine_id': self.machine_id,
                'start_time': current_time,
                'last_run_time': current_time,
                'status': 'trial'
            }
            self._save_license(data)
            self.status = 'trial'
            self.remaining_days = self.TRIAL_DAYS
            return True, f"欢迎试用！您还有 {self.TRIAL_DAYS} 天试用期。"

        # 情况2: 文件被篡改或损坏
        if data.get('status') in ['tampered', 'corrupted']:
            self.status = 'tampered'
            return False, "许可证文件损坏或被篡改，请联系管理员。"

        # 情况3: 机器码不匹配（直接拷贝文件到另一台机器）
        if data.get('machine_id') != self.machine_id:
            self.status = 'tampered'
            return False, "许可证与当前硬件不匹配。"

        # 情况4: 已激活
        if data.get('status') == 'activated':
            self.status = 'activated'
            return True, "已激活专业版。"

        # 情况5: 试用期检查
        start_time = data.get('start_time', current_time)
        last_run_time = data.get('last_run_time', current_time)
        
        # 检查系统时间是否倒流
        if current_time < last_run_time:
            self.status = 'tampered'
            return False, "系统时间异常，请校准时间。"
            
        # 更新最后运行时间
        data['last_run_time'] = current_time
        self._save_license(data)
        
        elapsed_seconds = current_time - start_time
        elapsed_days = elapsed_seconds / (24 * 3600)
        
        if elapsed_days > self.TRIAL_DAYS:
            self.status = 'expired'
            self.remaining_days = 0
            return False, "试用期已结束，请购买激活码。"
        else:
            self.status = 'trial'
            remaining = self.TRIAL_DAYS - elapsed_days
            self.remaining_days = max(0, int(remaining) + 1) # 向上取整显示天数
            # 格式化显示剩余时间，如果小于1天显示小时
            if remaining < 1:
                hours = int(remaining * 24)
                return True, f"试用期剩余 {hours} 小时。"
            return True, f"试用期剩余 {self.remaining_days} 天。"

    def validate_activation_code(self, code):
        """
        验证激活码
        算法: MD5(MachineID + SECRET_KEY + "ACTIVATED")[8:24] (取中间16位)
        """
        code = code.strip().upper()
        # 生成预期激活码
        raw = f"{self.machine_id}{self.SECRET_KEY}ACTIVATED"
        expected = hashlib.md5(raw.encode()).hexdigest().upper()[8:24]
        
        return code == expected

    def activate(self, code):
        """尝试激活"""
        if self.validate_activation_code(code):
            data = self._load_license()
            if not data or data.get('status') in ['tampered', 'corrupted']:
                # 如果文件坏了，重置一个新的激活文件
                data = {
                    'machine_id': self.machine_id,
                    'start_time': time.time(),
                }
            
            data['status'] = 'activated'
            data['activation_time'] = time.time()
            data['last_run_time'] = time.time()
            
            self._save_license(data)
            self.status = 'activated'
            return True, "激活成功！"
        else:
            return False, "激活码无效。"

# 单例实例
license_manager = LicenseManager()
