import os
from dotenv import load_dotenv
from types import SimpleNamespace

# 加载环境变量
load_dotenv()

# 创建配置对象
config = SimpleNamespace()

# SOAR配置
config.SOAR_API_URL = os.getenv('SOAR_API_URL', 'https://api.example-soar.com')
config.SOAR_API_TOKEN = os.getenv('SOAR_API_TOKEN', 'your_soar_api_token')
config.SOAR_API_TIMEOUT = int(os.getenv('SOAR_API_TIMEOUT', 30))
config.SOAR_RETRY_COUNT = int(os.getenv('SOAR_RETRY_COUNT', 3))
config.SOAR_RETRY_DELAY = int(os.getenv('SOAR_RETRY_DELAY', 5))
config.SOAR_VERIFY_SSL = os.getenv('SOAR_VERIFY_SSL', 'True').lower() == 'true'

# LLM配置
config.LLM_BASE_URL = os.getenv('LLM_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
config.LLM_API_KEY = os.getenv('LLM_API_KEY', 'your_llm_api_key')
config.LLM_MODEL = os.getenv('LLM_MODEL', 'qwen-plus')
config.LLM_MODEL_LONG_TEXT = os.getenv('LLM_MODEL_LONG_TEXT', 'qwen-long')
config.LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', 0.6))

# 事件处理配置
config.EVENT_MAX_ROUND = int(os.getenv('EVENT_MAX_ROUND', 3))

# Expert Service Worker Intervals (seconds)
config.EXPERT_EXECUTION_SUMMARY_INTERVAL = int(os.getenv('EXPERT_EXECUTION_SUMMARY_INTERVAL', 10))
config.EXPERT_COMMAND_STATUS_INTERVAL = int(os.getenv('EXPERT_COMMAND_STATUS_INTERVAL', 10))
config.EXPERT_TASK_STATUS_INTERVAL = int(os.getenv('EXPERT_TASK_STATUS_INTERVAL', 15))
config.EXPERT_EVENT_ROUND_STATUS_INTERVAL = int(os.getenv('EXPERT_EVENT_ROUND_STATUS_INTERVAL', 20))
config.EXPERT_EVENT_SUMMARY_INTERVAL = int(os.getenv('EXPERT_EVENT_SUMMARY_INTERVAL', 30))
config.EXPERT_EVENT_NEXT_ROUND_INTERVAL = int(os.getenv('EXPERT_EVENT_NEXT_ROUND_INTERVAL', 25))


config.EXPERT_LIFECYCLE_INTERVAL  = int(os.getenv('EXPERT_LIFECYCLE_INTERVAL', 10)) 
config.EXPERT_LIFECYCLE_INTERVAL_ERROR = int(os.getenv('EXPERT_LIFECYCLE_INTERVAL_ERROR', 15))

# 其他配置
config.DEBUG = os.getenv('DEBUG', 'False').lower() == 'true' 