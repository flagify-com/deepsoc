"""
TestApp 版本信息
"""

__version__ = "1.0.0"
__version_info__ = (1, 0, 0)

# 版本元数据
VERSION_MAJOR = 1
VERSION_MINOR = 0
VERSION_PATCH = 0

def get_version():
    """获取版本字符串"""
    return f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"

def get_version_info():
    """获取版本详细信息"""
    import datetime
    import platform
    import sys
    
    return {
        "version": get_version(),
        "version_tuple": (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH),
        "build_date": "2025-07-06",
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "description": "测试应用",
        "project_name": "TestApp"
    }

def print_version():
    """打印版本信息"""
    info = get_version_info()
    print("=" * 50)
    print(f"🚀 {info['project_name']} - {info['description']}")
    print("=" * 50)
    print(f"版本: {info['version']}")
    print(f"构建日期: {info['build_date']}")
    print(f"Python版本: {info['python_version']}")
    print(f"运行平台: {info['platform']}")
    print("=" * 50)

# 版本比较函数
def version_compare(version1, version2):
    """比较两个版本号"""
    def normalize(v):
        return [int(x) for x in v.split('.')]
    
    v1_parts = normalize(version1)
    v2_parts = normalize(version2)
    
    # 补齐长度
    max_len = max(len(v1_parts), len(v2_parts))
    v1_parts.extend([0] * (max_len - len(v1_parts)))
    v2_parts.extend([0] * (max_len - len(v2_parts)))
    
    if v1_parts < v2_parts:
        return -1
    elif v1_parts > v2_parts:
        return 1
    else:
        return 0
