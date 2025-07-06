#!/usr/bin/env python3
"""
TestApp 主程序
"""
import argparse
import sys
from version import __version__, print_version

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='测试应用')
    parser.add_argument('--version', action='store_true', help='显示版本信息')
    
    args = parser.parse_args()
    
    if args.version:
        print_version()
        return
    
    # 启动时显示版本
    print(f"🚀 TestApp v{__version__} 启动")
    
    # 你的应用逻辑在这里
    print("应用运行中...")
    print("使用 --version 查看版本信息")

if __name__ == '__main__':
    main()
