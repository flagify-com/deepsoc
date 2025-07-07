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

# 列出所有用户
with app.app_context():
    users = User.query.all()
    if not users:
        print('数据库中没有用户')
    else:
        print(f'共有 {len(users)} 个用户:')
        for user in users:
            print(f'用户名: {user.username}, 邮箱: {user.email}, 角色: {user.role}, 最后登录: {user.last_login_at}') 