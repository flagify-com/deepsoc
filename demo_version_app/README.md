# TestApp

测试应用

## 版本信息

当前版本: 1.0.0

## 安装和运行

```bash
# 运行应用
python main.py

# 查看版本信息
python main.py --version
```

## 版本管理

```bash
# 查看当前版本
python version_manager.py show

# 升级版本
python version_manager.py patch   # 1.0.0 → 1.0.1
python version_manager.py minor   # 1.0.0 → 1.1.0
python version_manager.py major   # 1.0.0 → 2.0.0

# 设置特定版本
python version_manager.py set 1.5.0

# 创建Git标签
python version_manager.py tag
```

## 更新日志

### [1.0.0] - 2025-07-06
- 初始版本
