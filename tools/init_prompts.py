#!/usr/bin/env python3
"""Import markdown prompts into the database.

Usage:
    python tools/init_prompts.py
"""
import os
from dotenv import load_dotenv
from flask import Flask
from app.models.models import db, Prompt
from app.prompts.default_prompts import DEFAULT_PROMPTS

load_dotenv(override=True)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'mysql+pymysql://deepsoc_user:deepsoc_password@localhost:3306/deepsoc')

db.init_app(app)


def load_prompt_to_db(name: str, content: str) -> None:
    """Store the given prompt text into the database."""
    with app.app_context():
        prompt = Prompt.query.filter_by(name=name).first()
        if not prompt:
            prompt = Prompt(name=name)
            db.session.add(prompt)
        prompt.content = content
        db.session.commit()


def main():
    for name, content in DEFAULT_PROMPTS.items():
        load_prompt_to_db(name, content)
    print('Prompts imported.')


if __name__ == '__main__':
    main()
