#!/usr/bin/env python3
"""Utility to build prompts for different roles."""
from app.models.models import Prompt

ROLE_NAMES = {
    '_captain': 'role_soc_captain',
    '_manager': 'role_soc_manager',
    '_operator': 'role_soc_operator',
    '_expert': 'role_soc_expert',
}

BACKGROUND_SECURITY = 'background_security'
BACKGROUND_PLAYBOOKS = 'background_soar_playbooks'


def generate_prompt(role: str) -> str:
    """Generate prompt text for the given role."""
    name = ROLE_NAMES.get(role, '')
    if not name:
        return ''

    role_prompt = Prompt.query.filter_by(name=name).first()
    if not role_prompt:
        return ''

    background = Prompt.query.filter_by(name=BACKGROUND_SECURITY).first()
    playbooks = Prompt.query.filter_by(name=BACKGROUND_PLAYBOOKS).first()

    prompt = role_prompt.content
    prompt = prompt.replace('{background_info}', background.content if background else '')
    prompt = prompt.replace('{playbook_list}', playbooks.content if playbooks else '')
    return prompt


def main():
    for role in ROLE_NAMES:
        text = generate_prompt(role)
        print(f"==== {role} ====")
        print(text[:200] + ('...' if len(text) > 200 else ''))


if __name__ == '__main__':
    main()
