import os
from datetime import timedelta

# Flask 配置
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_secret_key_change_in_production')
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt_secret_key_change_in_production')
JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=1)

# 数据库配置
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', '@Ai15173537562'),
    'database': os.environ.get('DB_NAME', 'marking_system'),
    'max_connections': int(os.environ.get('DB_MAX_CONNECTIONS', 10))
}

# 激活码配置
ACTIVATION_CODE_LENGTH = 16
MAX_ACTIVATIONS_PER_CODE = 3  # 每个激活码最多可以激活的设备数量
