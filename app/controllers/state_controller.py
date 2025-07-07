from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import db, GlobalSetting
import logging

state_bp = Blueprint('state', __name__)
logger = logging.getLogger(__name__)


@state_bp.route('/driving-mode', methods=['GET', 'PUT'])
@jwt_required()
def driving_mode():
    """Get or update global driving mode."""
    setting = GlobalSetting.query.filter_by(key='driving_mode').first()
    if request.method == 'GET':
        mode = setting.value if setting else 'auto'
        return jsonify({'status': 'success', 'data': {'mode': mode}})

    data = request.get_json() or {}
    mode = data.get('mode')
    if mode not in ['auto', 'manual']:
        return jsonify({'status': 'error', 'message': 'Invalid mode'}), 400
    if not setting:
        setting = GlobalSetting(key='driving_mode')
        db.session.add(setting)
    setting.value = mode
    db.session.commit()
    logger.info(f"Driving mode updated to {mode}")
    return jsonify({'status': 'success', 'data': {'mode': mode}})

