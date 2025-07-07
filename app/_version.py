"""
DeepSOC 版本信息
"""

__version__ = "1.8.2"
__version_info__ = (1, 8, 2)

# 版本元数据
VERSION_MAJOR = 1
VERSION_MINOR = 8
VERSION_PATCH = 2
VERSION_BUILD = None

# 构建完整版本字符串
def get_version():
    """获取完整版本字符串"""
    version = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"
    if VERSION_BUILD:
        version += f".{VERSION_BUILD}"
    return version

# 获取版本详细信息
def get_version_info():
    """获取版本详细信息"""
    import datetime
    
    return {
        "version": get_version(),
        "version_info": (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH),
        "build_date": "2025-07-07",  # 可以通过CI/CD自动更新
        "python_version": None,  # 运行时填充
        "git_commit": None,      # 可以通过CI/CD自动更新
        "release_name": "移除根目录无用文件",
        "description": "AI-Powered Security Operations Center with Multi-Agent Architecture"
    }

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

# 检查是否为开发版本
def is_dev_version():
    """检查是否为开发版本"""
    return VERSION_BUILD is not None or "dev" in get_version()

# 获取简短版本信息
def get_short_version():
    """获取简短版本信息"""
    return f"v{get_version()}"

# 版本历史（主要版本）
VERSION_HISTORY = {
    "1.0.0": "Initial release with multi-agent architecture",
    "1.1.0": "Enhanced user experience with engineer chat and message display improvements"
}