#!/usr/bin/env python3
"""
啟動小盤動量交易機械人 - 跨平臺

用法:
    python run.py

或在 Windows 上:
    python run.py
"""
import sys
import os

# 獲取項目根目錄（run.py 所在的目錄）
project_root = os.path.dirname(os.path.abspath(__file__))

# 確保項目根目錄在 Python 路徑的最前面
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"Python Path: {project_root}")
print(f"Python Version: {sys.version}")
print()

# 驗證必要的目錄和模塊
required_dirs = ['config', 'core', 'utils', 'backtest']
for dir_name in required_dirs:
    dir_path = os.path.join(project_root, dir_name)
    if os.path.isdir(dir_path):
        print(f"✅ Found: {dir_name}/")
    else:
        print(f"❌ Missing: {dir_name}/")
        sys.exit(1)

print()

# 現在導入機械人
try:
    from small_cap_momentum_bot_main import main
    main()
except ModuleNotFoundError as e:
    print(f"❌ Module Import Error: {e}")
    print(f"\nCurrent working directory: {os.getcwd()}")
    print(f"Project root: {project_root}")
    print(f"Python path: {sys.path}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
