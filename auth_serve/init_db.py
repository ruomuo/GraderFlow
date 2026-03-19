import pymysql
import hashlib
import uuid
import sys
from config import DB_CONFIG
import secrets
import string

def create_database():
    # 连接到MySQL服务器（不指定数据库）
    conn = pymysql.connect(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password']
    )

    try:
        with conn.cursor() as cursor:
            # 创建数据库
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']} DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"Database '{DB_CONFIG['database']}' created or already exists.")
    finally:
        conn.close()


def init_tables():
    # 连接到指定的数据库
    conn = pymysql.connect(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['database']
    )

    try:
        with conn.cursor() as cursor:
            # 用户表
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password_hash VARCHAR(128) NOT NULL,
                email VARCHAR(100),
                is_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP NULL,
                status ENUM('active', 'inactive', 'suspended') DEFAULT 'active'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("Table 'users' created or already exists.")

            # 激活码表
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS activation_codes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                code VARCHAR(32) NOT NULL UNIQUE,
                max_activations INT DEFAULT 3,
                current_activations INT DEFAULT 0,
                created_by INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NULL,
                status ENUM('active', 'inactive', 'expired') DEFAULT 'active',
                FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("Table 'activation_codes' created or already exists.")

            # 设备表
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id INT AUTO_INCREMENT PRIMARY KEY,
                hardware_id VARCHAR(64) NOT NULL UNIQUE,
                hostname VARCHAR(100),
                os_info VARCHAR(100),
                first_activation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_verification_time TIMESTAMP NULL,
                status ENUM('active', 'inactive', 'blocked') DEFAULT 'active'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("Table 'devices' created or already exists.")

            # 激活记录表
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS activations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                activation_code_id INT NOT NULL,
                device_id INT NOT NULL,
                activation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expiration_time TIMESTAMP NULL,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (activation_code_id) REFERENCES activation_codes(id) ON DELETE CASCADE,
                FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
                UNIQUE KEY (activation_code_id, device_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("Table 'activations' created or already exists.")

            # 登录日志表
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS login_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address VARCHAR(45),
                user_agent VARCHAR(255),
                status ENUM('success', 'failed') NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("Table 'login_logs' created or already exists.")

            # 添加默认管理员账户
            admin_exists = cursor.execute("SELECT id FROM users WHERE username = 'admin'")
            if not admin_exists:
                admin_password = "admin123"  # 默认密码，生产环境应更改
                password_hash = hashlib.sha256(admin_password.encode()).hexdigest()
                cursor.execute(
                    "INSERT INTO users (username, password_hash, is_admin, status) VALUES (%s, %s, %s, %s)",
                    ("admin", password_hash, True, "active")
                )
                print("Default admin user created.")

            # 生成100个复杂激活码
            alphabet = string.ascii_letters + string.digits  # 62个字符
            activation_codes = set()

            # 确保生成100个唯一激活码
            while len(activation_codes) < 100:
                # 生成32位随机码（4组4字符，用连字符连接）
                segments = [''.join(secrets.choice(alphabet) for _ in range(4)) for _ in range(4)]
                code = '-'.join(segments)

                # 添加校验机制：必须包含数字和字母
                if any(c.isdigit() for c in code) and any(c.isalpha() for c in code):
                    activation_codes.add(code)

            # 获取管理员ID（用于created_by字段）
            cursor.execute("SELECT id FROM users WHERE username = 'admin'")
            admin_id = cursor.fetchone()[0] if cursor.rowcount > 0 else None

            # 批量插入激活码
            insert_query = """
            INSERT INTO activation_codes 
                (code, max_activations, status, created_by, expires_at)
            VALUES (%s, %s, 'inactive', %s, NULL)
            ON DUPLICATE KEY UPDATE code=code  -- 避免重复
            """

            # 设置参数：最大激活次数3次，状态inactive
            batch_data = [(code, 3, admin_id) for code in activation_codes]
            cursor.executemany(insert_query, batch_data)

            print(f"Generated {len(activation_codes)} unique activation codes")
            conn.commit()
    except Exception as e:
        print(f"Error initializing tables: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        create_database()
        init_tables()
        print("Database initialization completed successfully.")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        sys.exit(1)