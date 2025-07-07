# 控制器包初始化文件
from flask import Blueprint

from .event_controller import event_bp
from .socket_controller import register_socket_events, broadcast_message
from .auth_controller import auth_bp
from .prompt_controller import prompt_bp
from .state_controller import state_bp

__all__ = [
    'event_bp',
    'register_socket_events',
    'broadcast_message',
    'auth_bp',
    'prompt_bp',
    'state_bp',
]
