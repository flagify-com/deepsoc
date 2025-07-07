import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models.models import Prompt, db

prompt_bp = Blueprint('prompt', __name__)
logger = logging.getLogger(__name__)

ROLE_NAMES = {
    '_captain': 'role_soc_captain',
    '_manager': 'role_soc_manager',
    '_operator': 'role_soc_operator',
    '_expert': 'role_soc_expert'
}

BACKGROUND_NAMES = {
    'background_security': 'background_security',
    'background_soar_playbooks': 'background_soar_playbooks',
    'mcp_tools': 'mcp_tools'
}


def _load_prompt(role: str) -> str:
    name = ROLE_NAMES[role]
    prompt = Prompt.query.filter_by(name=name).first()
    return prompt.content if prompt else ''


def _save_prompt(role: str, content: str) -> None:
    name = ROLE_NAMES[role]
    prompt = Prompt.query.filter_by(name=name).first()
    if not prompt:
        prompt = Prompt(name=name)
        db.session.add(prompt)
    prompt.content = content
    db.session.commit()


def _load_background(name: str) -> str:
    key = BACKGROUND_NAMES[name]
    prompt = Prompt.query.filter_by(name=key).first()
    return prompt.content if prompt else ''


def _save_background(name: str, content: str) -> None:
    key = BACKGROUND_NAMES[name]
    prompt = Prompt.query.filter_by(name=key).first()
    if not prompt:
        prompt = Prompt(name=key)
        db.session.add(prompt)
    prompt.content = content
    db.session.commit()


@prompt_bp.route('/list', methods=['GET'])
@jwt_required()
def list_prompts():
    """Return prompts for all supported roles."""
    prompts = {role: _load_prompt(role) for role in ROLE_NAMES}
    return jsonify({'status': 'success', 'data': prompts})


@prompt_bp.route('/<role>', methods=['GET', 'PUT'])
@jwt_required()
def handle_prompt(role):
    """Get or update prompt for a specific role."""
    if role not in ROLE_NAMES:
        return jsonify({'status': 'error', 'message': '未知角色'}), 400

    if request.method == 'GET':
        return jsonify({'status': 'success', 'data': _load_prompt(role)})

    data = request.get_json() or {}
    content = data.get('prompt', '')
    try:
        _save_prompt(role, content)
        return jsonify({'status': 'success', 'message': '保存成功'})
    except Exception as e:
        logger.error(f'保存提示词失败: {e}')
        return jsonify({'status': 'error', 'message': '保存失败'}), 500


@prompt_bp.route('/background/<name>', methods=['GET', 'PUT'])
@jwt_required()
def handle_background(name):
    """Get or update background files."""
    if name not in BACKGROUND_NAMES:
        return jsonify({'status': 'error', 'message': '未知文件'}), 400

    if request.method == 'GET':
        return jsonify({'status': 'success', 'data': _load_background(name)})

    data = request.get_json() or {}
    content = data.get('content', '')
    try:
        _save_background(name, content)
        return jsonify({'status': 'success', 'message': '保存成功'})
    except Exception as e:
        logger.error(f'保存背景文件失败: {e}')
        return jsonify({'status': 'error', 'message': '保存失败'}), 500
