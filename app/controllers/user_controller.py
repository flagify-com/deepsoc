import logging
from flask import Blueprint, request, jsonify
import os
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import IntegrityError

from app.models.models import db, User

logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__)


def admin_required(func):
    """Ensure the current user is admin."""
    @jwt_required()
    def wrapper(*args, **kwargs):
        username = get_jwt_identity()
        current_user = User.query.filter_by(username=username).first()
        if not current_user or current_user.role != 'admin':
            return jsonify({'status': 'error', 'message': '只有管理员可以执行此操作'}), 403
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


@user_bp.route('/list', methods=['GET'])
@admin_required
def list_users():
    users = User.query.all()
    return jsonify({'status': 'success', 'data': [u.to_dict() for u in users]})


@user_bp.route('', methods=['POST'])
@admin_required
def create_user():
    data = request.get_json() or {}
    if not all(k in data for k in ('username', 'email', 'password')):
        return jsonify({'status': 'error', 'message': '用户名、邮箱和密码都是必填项'}), 400
    try:
        new_user = User(
            username=data['username'],
            nickname=data.get('nickname'),
            email=data['email'],
            phone=data.get('phone'),
            role=data.get('role', 'user')
        )
        new_user.set_password(data['password'])
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'status': 'success', 'data': new_user.to_dict()}), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': '用户名或邮箱已存在'}), 409
    except Exception as e:
        db.session.rollback()
        logger.error(f'创建用户失败: {e}')
        return jsonify({'status': 'error', 'message': '创建用户失败'}), 500


@user_bp.route('/<int:user_id>', methods=['GET'])
@admin_required
def get_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'status': 'error', 'message': '用户不存在'}), 404
    return jsonify({'status': 'success', 'data': user.to_dict()})


@user_bp.route('/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'status': 'error', 'message': '用户不存在'}), 404
    data = request.get_json() or {}
    admin_username = os.getenv('ADMIN_USERNAME', 'admin')
    if user.username == admin_username and 'role' in data:
        if data['role'] != user.role:
            return jsonify({'status': 'error', 'message': '初始管理员角色不可修改'}), 400
    if 'email' in data and data['email']:
        user.email = data['email']
    if 'nickname' in data:
        user.nickname = data['nickname']
    if 'phone' in data:
        user.phone = data['phone']
    if 'role' in data:
        user.role = data['role']
    if 'is_active' in data:
        user.is_active = bool(data['is_active'])
    db.session.commit()
    return jsonify({'status': 'success', 'data': user.to_dict()})


@user_bp.route('/<int:user_id>/password', methods=['PUT'])
@admin_required
def update_user_password(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'status': 'error', 'message': '用户不存在'}), 404
    data = request.get_json() or {}
    new_password = data.get('password')
    if not new_password:
        return jsonify({'status': 'error', 'message': '密码不能为空'}), 400
    user.set_password(new_password)
    db.session.commit()
    return jsonify({'status': 'success', 'message': '密码更新成功'})


@user_bp.route('/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'status': 'error', 'message': '用户不存在'}), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({'status': 'success', 'message': '用户已删除'})
