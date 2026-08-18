#!/usr/bin/env python3
"""
診斷脚本 - 檢查環境和配置
"""
import sys
import os

print("=" * 60)
print("【Small-Cap Momentum Trader - 環境診斷】")
print("=" * 60)
print()

# 1. Python 版本
print("1️⃣ Python 版本")
print(f"   {sys.version}")
print()

# 2. 工作目錄
print("2️⃣ 工作目錄")
print(f"   {os.getcwd()}")
print()

# 3. 項目根目錄
project_root = os.path.dirname(os.path.abspath(__file__))
print("3️⃣ 項目根目錄")
print(f"   {project_root}")
print()

# 4. 檢查必要的目錄
print("4️⃣ 目錄結構")
required_dirs = ['config', 'core', 'utils', 'backtest', 'tradingview', 'logs']
for dir_name in required_dirs:
    dir_path = os.path.join(project_root, dir_name)
    exists = "✅" if os.path.isdir(dir_path) else "❌"
    print(f"   {exists} {dir_name}/")
print()

# 5. 檢查必要的文件
print("5️⃣ 必要文件")
required_files = [
    'small_cap_momentum_bot_main.py',
    'run.py',
    'requirements.txt',
    'config/settings.py',
    'config/__init__.py',
    'core/__init__.py'
]
for file_name in required_files:
    file_path = os.path.join(project_root, file_name)
    exists = "✅" if os.path.isfile(file_path) else "❌"
    print(f"   {exists} {file_name}")
print()

# 6. 檢查 Python 路徑
print("6️⃣ Python 路徑")
for i, path in enumerate(sys.path[:5]):
    print(f"   [{i}] {path}")
if len(sys.path) > 5:
    print(f"   ... ({len(sys.path) - 5} more paths)")
print()

# 7. 嘗試導入模塊
print("7️⃣ 模塊導入測試")
sys.path.insert(0, project_root)

modules_to_test = [
    'config',
    'config.settings',
    'core',
    'core.small_cap_momentum_bot_ibkr_client',
    'utils',
    'utils.logger'
]

for module_name in modules_to_test:
    try:
        __import__(module_name)
        print(f"   ✅ {module_name}")
    except Exception as e:
        print(f"   ❌ {module_name}")
        print(f"      Error: {e}")

print()

# 8. 檢查依賴
print("8️⃣ 依賴包檢查")
dependencies = ['ib_async', 'pandas', 'pytz', 'numpy', 'dotenv']
for dep in dependencies:
    try:
        __import__(dep.replace('-', '_'))
        print(f"   ✅ {dep}")
    except ImportError:
        print(f"   ❌ {dep} (未安裝)")

print()

# 9. 配置檢查
print("9️⃣ 配置驗證")
try:
    from config.settings import IB_HOST, IB_PORT, IB_CLIENT_ID, PAPER_TRADING
    print(f"   ✅ IBKR Host: {IB_HOST}:{IB_PORT}")
    print(f"   ✅ Client ID: {IB_CLIENT_ID}")
    print(f"   ✅ Paper Trading: {PAPER_TRADING}")
except Exception as e:
    print(f"   ❌ 無法加載配置: {e}")

print()
print("=" * 60)
print("✅ 診斷完成")
print("=" * 60)
