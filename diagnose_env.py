#!/usr/bin/env python3
"""診斷 .env 文件加載問題"""

import os
from pathlib import Path

print("=" * 80)
print("🔍 環境變數診斷")
print("=" * 80)

# 1. 檢查當前工作目錄
print(f"\n📁 當前工作目錄: {os.getcwd()}")

# 2. 檢查 .env 文件是否存在
env_path = Path(".env")
print(f"📁 .env 文件路徑: {env_path.resolve()}")
print(f"✓ .env 文件存在: {env_path.exists()}")

if env_path.exists():
    with open(".env", "r", encoding="utf-8") as f:
        content = f.read()
    print(f"📄 .env 文件大小: {len(content)} 字節")
    print(f"\n📄 .env 文件內容預覽:")
    for line in content.split("\n"):
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            # 只顯示密鑰的前5個和後5個字符
            if len(value) > 10:
                masked_value = value[:5] + "***" + value[-5:]
            else:
                masked_value = "***" if value else "(空)"
            print(f"  {key} = {masked_value}")
        elif line.startswith("#") or not line.strip():
            continue

# 3. 嘗試手動加載 .env
print(f"\n🔧 嘗試加載 .env...")
from dotenv import load_dotenv

result = load_dotenv(".env")
print(f"✓ load_dotenv() 結果: {result}")

# 4. 檢查環境變數是否被設置
print(f"\n🔑 檢查環境變數:")

api_key = os.getenv("ALPACA_API_KEY")
secret_key = os.getenv("ALPACA_SECRET_KEY")
base_url = os.getenv("ALPACA_BASE_URL")

print(f"  ALPACA_API_KEY: {'✓ 已設置' if api_key else '❌ 未設置'}")
if api_key:
    print(f"    值: {api_key[:10]}...{api_key[-10:]}")

print(f"  ALPACA_SECRET_KEY: {'✓ 已設置' if secret_key else '❌ 未設置'}")
if secret_key:
    print(f"    值: {secret_key[:10]}...{secret_key[-10:]}")

print(f"  ALPACA_BASE_URL: {'✓ 已設置' if base_url else '❌ 未設置'}")
if base_url:
    print(f"    值: {base_url}")

# 5. 現在測試 config.settings
print(f"\n🧪 測試 config.settings 模塊:")
try:
    from config.settings import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL

    print(f"  ALPACA_API_KEY: {'✓ 已加載' if ALPACA_API_KEY else '❌ 未加載'}")
    if ALPACA_API_KEY:
        print(f"    值: {ALPACA_API_KEY[:10]}...{ALPACA_API_KEY[-10:]}")

    print(f"  ALPACA_SECRET_KEY: {'✓ 已加載' if ALPACA_SECRET_KEY else '❌ 未加載'}")
    if ALPACA_SECRET_KEY:
        print(f"    值: {ALPACA_SECRET_KEY[:10]}...{ALPACA_SECRET_KEY[-10:]}")

    print(f"  ALPACA_BASE_URL: {'✓ 已加載' if ALPACA_BASE_URL else '❌ 未加載'}")
    if ALPACA_BASE_URL:
        print(f"    值: {ALPACA_BASE_URL}")

except Exception as e:
    print(f"  ❌ 錯誤: {e}")

print("\n" + "=" * 80)
print("診斷完成")
print("=" * 80)
