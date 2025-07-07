from app.models.models import db, User
from flask import Flask
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(override=True)

# 创建Flask应用
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'mysql+pymysql://deepsoc_user:deepsoc_password@localhost:3306/deepsoc')
db.init_app(app)

# 创建admin用户
with app.app_context():
    # 检查admin是否已存在
    existing_admin = User.query.filter_by(username='admin').first()
    if existing_admin:
        print('管理员账号已存在，无需重新创建')
    else:
        admin = User(
            username='admin',
            email='admin@deepsoc.local',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print('管理员账号创建成功！')
        print('用户名: admin')
        print('密码: admin123') 