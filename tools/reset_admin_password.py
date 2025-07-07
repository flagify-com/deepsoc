from app.models.models import db, User
from flask import Flask
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 创建Flask应用
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'mysql+pymysql://deepsoc_user:deepsoc_password@localhost:3306/deepsoc')
db.init_app(app)

# 重置admin密码
with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        print('管理员账号不存在，创建新账号')
        admin = User(
            username='admin',
            email='admin@deepsoc.local',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print('管理员账号创建成功！')
    else:
        print('找到现有管理员账号，重置密码')
        admin.set_password('admin123')
        db.session.commit()
        print('密码重置成功')
    
    print('管理员信息:')
    print(f'用户名: {admin.username}')
    print(f'邮箱: {admin.email}')
    print(f'密码: admin123') 