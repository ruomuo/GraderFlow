from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import logging
import datetime

from config import SECRET_KEY, JWT_SECRET_KEY, DB_CONFIG
from db_operations import DatabaseOperations

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY

jwt = JWTManager(app)
db_ops = DatabaseOperations(DB_CONFIG)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@app.route('/api/register', methods=['POST'])
def register():
    """用户注册接口"""
    data = request.get_json()

    if not data or not all(k in data for k in ('username', 'password')):
        return jsonify({'message': '缺少必要参数'}), 400

    username = data.get('username')
    password = data.get('password')
    email = data.get('email')

    success, message = db_ops.create_user(username, password, email)

    if success:
        return jsonify({'message': message}), 201
    else:
        return jsonify({'message': message}), 400


@app.route('/api/login', methods=['POST'])
def login():
    """用户登录接口"""
    data = request.get_json()

    if not data or not all(k in data for k in ('username', 'password')):
        return jsonify({'message': '缺少必要参数'}), 400

    username = data.get('username')
    password = data.get('password')

    success, message, user_info = db_ops.verify_user(username, password)

    # 记录登录日志
    if user_info:
        db_ops.log_login(
            user_info['user_id'],
            request.remote_addr,
            request.headers.get('User-Agent', ''),
            'success' if success else 'failed'
        )

    if success:
        # 创建JWT令牌
        access_token = create_access_token(identity=user_info)
        return jsonify({
            'message': message,
            'access_token': access_token,
            'user_info': user_info
        }), 200
    else:
        return jsonify({'message': message}), 401


@app.route('/api/activate', methods=['POST'])
def activate():
    """软件激活接口"""
    data = request.get_json()

    if not data or not all(k in data for k in ('activation_code', 'hardware_id')):
        return jsonify({'message': '缺少必要参数'}), 400

    activation_code = data.get('activation_code')
    hardware_id = data.get('hardware_id')
    hostname = data.get('hostname')
    os_info = data.get('os_info')

    success, message = db_ops.activate_software(activation_code, hardware_id, hostname, os_info)

    if success:
        return jsonify({'message': message}), 201
    else:
        return jsonify({'message': message}), 400


@app.route('/api/verify', methods=['POST'])
def verify():
    """验证激活状态接口"""
    data = request.get_json()

    if not data or 'hardware_id' not in data:
        return jsonify({'message': '缺少必要参数'}), 400

    hardware_id = data.get('hardware_id')

    is_activated, message = db_ops.verify_activation(hardware_id)

    return jsonify({
        'is_activated': is_activated,
        'message': message
    }), 200


@app.route('/api/admin/users', methods=['GET'])
@jwt_required()
def get_users():
    """获取用户列表（仅管理员）"""
    current_user = get_jwt_identity()

    if not current_user or not current_user.get('is_admin'):
        return jsonify({'message': '权限不足'}), 403

    # 这里应该实现获取用户列表的逻辑
    # 由于不是核心功能，此处省略实现

    return jsonify({'message': '此功能尚未实现'}), 501


@app.route('/api/admin/activation_codes', methods=['GET', 'POST'])
@jwt_required()
def manage_activation_codes():
    """管理激活码（仅管理员）"""
    current_user = get_jwt_identity()

    if not current_user or not current_user.get('is_admin'):
        return jsonify({'message': '权限不足'}), 403

    # 这里应该实现管理激活码的逻辑
    # 由于不是核心功能，此处省略实现

    return jsonify({'message': '此功能尚未实现'}), 501


@app.errorhandler(404)
def not_found(error):
    return jsonify({'message': '请求的资源不存在'}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"服务器内部错误: {error}")
    return jsonify({'message': '服务器内部错误'}), 500