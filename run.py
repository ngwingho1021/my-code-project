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

# 添加項目根目錄到 Python 路徑
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 現在導入機械人
from small_cap_momentum_bot_main import main

if __name__ == "__main__":
    main()
