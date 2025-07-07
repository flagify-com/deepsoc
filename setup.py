"""
DeepSOC 安装配置文件
"""
import os
import sys
from setuptools import setup, find_packages

# 确保可以导入版本信息
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
from _version import __version__, get_version_info

# 读取 README 文件
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# 读取 requirements.txt
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

# 获取版本详细信息
version_info = get_version_info()

setup(
    name="deepsoc",
    version=__version__,
    author="DeepSOC Team",
    author_email="contact@deepsoc.com",
    description=version_info["description"],
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/flagify-com/deepsoc",
    project_urls={
        "Bug Tracker": "https://github.com/flagify-com/deepsoc/issues",
        "Documentation": "https://github.com/flagify-com/deepsoc/docs",
        "Source Code": "https://github.com/flagify-com/deepsoc",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Information Technology",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Security",
        "Topic :: System :: Monitoring",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=22.0",
            "flake8>=4.0",
            "mypy>=0.910",
        ],
        "docs": [
            "sphinx>=4.0",
            "sphinx-rtd-theme>=1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "deepsoc=main:main",
            "deepsoc-agent=main:start_agent_cli",
        ],
    },
    include_package_data=True,
    package_data={
        "app": [
            "static/**/*",
            "templates/**/*",
            "prompts/**/*",
        ],
    },
    zip_safe=False,
    keywords=[
        "security",
        "soc", 
        "ai",
        "automation",
        "incident-response",
        "multi-agent",
        "soar",
        "cybersecurity"
    ],
    license="MIT",
)