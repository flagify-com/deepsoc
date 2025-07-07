from app.prompts.generate_prompt import generate_prompt

class PromptService:
    def __init__(self, role=None):
        self.role = role

    def get_system_prompt(self, role=None):
        """获取指定角色的系统提示词"""
        role_to_use = role if role else self.role
        return generate_prompt(role_to_use)

