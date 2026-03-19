import hashlib
import time
import logging
from db_config import DatabasePool

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatabaseOperations:
    def __init__(self, db_config=None):
        if db_config:
            self.db_pool = DatabasePool(**db_config)
        else:
            self.db_pool = DatabasePool()

    def hash_password(self, password):
        """对密码进行哈希处理"""
        return hashlib.sha256(password.encode()).hexdigest()

    def user_exists(self, username):
        """检查用户是否存在"""
        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                return cursor.fetchone() is not None
        finally:
            conn.close()

    def create_user(self, username, password, email=None, is_admin=False):
        """创建新用户"""
        if self.user_exists(username):
            return False, "用户名已存在"

        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cursor:
                password_hash = self.hash_password(password)
                cursor.execute(
                    "INSERT INTO users (username, password_hash, email, is_admin) VALUES (%s, %s, %s, %s)",
                    (username, password_hash, email, is_admin)
                )
                conn.commit()
                return True, "用户创建成功"
        except Exception as e:
            conn.rollback()
            logger.error(f"创建用户失败: {e}")
            return False, f"创建用户失败: {str(e)}"
        finally:
            conn.close()

    def verify_user(self, username, password):
        """验证用户登录"""
        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, password_hash, is_admin, status FROM users WHERE username = %s",
                    (username,)
                )
                user = cursor.fetchone()

                if not user:
                    return False, "用户不存在", None

                if user['status'] != 'active':
                    return False, "用户账号已被禁用", None

                password_hash = self.hash_password(password)
                if password_hash != user['password_hash']:
                    return False, "密码错误", None

                # 更新最后登录时间
                cursor.execute(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s",
                    (user['id'],)
                )
                conn.commit()

                return True, "登录成功", {
                    "user_id": user['id'],
                    "username": username,
                    "is_admin": user['is_admin']
                }
        except Exception as e:
            conn.rollback()
            logger.error(f"验证用户失败: {e}")
            return False, f"验证用户失败: {str(e)}", None
        finally:
            conn.close()

    def log_login(self, user_id, ip_address, user_agent, status):
        """记录登录日志"""
        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO login_logs (user_id, ip_address, user_agent, status) VALUES (%s, %s, %s, %s)",
                    (user_id, ip_address, user_agent, status)
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"记录登录日志失败: {e}")
        finally:
            conn.close()

    def validate_activation_code(self, code):
        """验证激活码是否有效"""
        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """SELECT id, max_activations, current_activations, status, expires_at 
                       FROM activation_codes WHERE code = %s""",
                    (code,)
                )
                code_info = cursor.fetchone()

                if not code_info:
                    return False, "激活码不存在", None

                if code_info['status'] != 'active':
                    return False, "激活码已失效", None

                if code_info['expires_at'] and code_info['expires_at'] < time.strftime('%Y-%m-%d %H:%M:%S'):
                    cursor.execute(
                        "UPDATE activation_codes SET status = 'expired' WHERE id = %s",
                        (code_info['id'],)
                    )
                    conn.commit()
                    return False, "激活码已过期", None

                if code_info['current_activations'] >= code_info['max_activations']:
                    return False, "激活码已达到最大激活次数", None

                return True, "激活码有效", code_info
        except Exception as e:
            logger.error(f"验证激活码失败: {e}")
            return False, f"验证激活码失败: {str(e)}", None
        finally:
            conn.close()

    def get_device_by_hardware_id(self, hardware_id):
        """根据硬件ID获取设备信息"""
        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, status FROM devices WHERE hardware_id = %s",
                    (hardware_id,)
                )
                return cursor.fetchone()
        finally:
            conn.close()

    def create_device(self, hardware_id, hostname=None, os_info=None):
        """创建新设备记录"""
        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO devices (hardware_id, hostname, os_info) VALUES (%s, %s, %s)",
                    (hardware_id, hostname, os_info)
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            conn.rollback()
            logger.error(f"创建设备记录失败: {e}")
            return None
        finally:
            conn.close()

    def create_activation(self, activation_code_id, device_id, expiration_time=None):
        """创建激活记录"""
        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cursor:
                # 检查是否已存在激活记录
                cursor.execute(
                    "SELECT id FROM activations WHERE activation_code_id = %s AND device_id = %s",
                    (activation_code_id, device_id)
                )
                existing = cursor.fetchone()

                if existing:
                    # 更新现有记录
                    cursor.execute(
                        "UPDATE activations SET is_active = TRUE, activation_time = CURRENT_TIMESTAMP, "
                        "expiration_time = %s WHERE id = %s",
                        (expiration_time, existing['id'])
                    )
                else:
                    # 创建新记录
                    cursor.execute(
                        "INSERT INTO activations (activation_code_id, device_id, expiration_time) VALUES (%s, %s, %s)",
                        (activation_code_id, device_id, expiration_time)
                    )

                # 更新激活码的当前激活次数
                cursor.execute(
                    "UPDATE activation_codes SET current_activations = "
                    "(SELECT COUNT(*) FROM activations WHERE activation_code_id = %s AND is_active = TRUE) "
                    "WHERE id = %s",
                    (activation_code_id, activation_code_id)
                )

                conn.commit()
                return True
        except Exception as e:
            conn.rollback()
            logger.error(f"创建激活记录失败: {e}")
            return False
        finally:
            conn.close()

    def activate_software(self, activation_code, hardware_id, hostname=None, os_info=None):
        """激活软件"""
        # 验证激活码
        valid, message, code_info = self.validate_activation_code(activation_code)
        if not valid:
            return False, message

        # 检查设备是否已存在
        device = self.get_device_by_hardware_id(hardware_id)
        if device:
            if device['status'] != 'active':
                return False, "此设备已被禁用"
            device_id = device['id']
        else:
            # 创建新设备记录
            device_id = self.create_device(hardware_id, hostname, os_info)
            if not device_id:
                return False, "创建设备记录失败"

        # 创建激活记录
        if self.create_activation(code_info['id'], device_id):
            return True, "软件激活成功"
        else:
            return False, "创建激活记录失败"

    def verify_activation(self, hardware_id):
        """验证设备是否已激活"""
        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cursor:
                # 获取设备信息
                cursor.execute(
                    "SELECT id, status FROM devices WHERE hardware_id = %s",
                    (hardware_id,)
                )
                device = cursor.fetchone()

                if not device:
                    return False, "设备未注册"

                if device['status'] != 'active':
                    return False, "设备已被禁用"

                # 检查是否有有效的激活记录
                cursor.execute(
                    """SELECT a.id, a.activation_time, a.expiration_time, a.is_active, ac.code 
                       FROM activations a 
                       JOIN activation_codes ac ON a.activation_code_id = ac.id 
                       WHERE a.device_id = %s AND a.is_active = TRUE""",
                    (device['id'],)
                )
                activation = cursor.fetchone()

                if not activation:
                    return False, "设备未激活"

                # 检查激活是否过期
                if activation['expiration_time'] and activation['expiration_time'] < time.strftime('%Y-%m-%d %H:%M:%S'):
                    cursor.execute(
                        "UPDATE activations SET is_active = FALSE WHERE id = %s",
                        (activation['id'],)
                    )
                    conn.commit()
                    return False, "激活已过期"

                # 更新最后验证时间
                cursor.execute(
                    "UPDATE devices SET last_verification_time = CURRENT_TIMESTAMP WHERE id = %s",
                    (device['id'],)
                )
                conn.commit()

                return True, "设备已激活"
        except Exception as e:
            logger.error(f"验证激活状态失败: {e}")
            return False, f"验证激活状态失败: {str(e)}"
        finally:
            conn.close()