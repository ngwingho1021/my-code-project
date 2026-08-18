#!/bin/bash
# Small-Cap Momentum Trader - macOS/Linux 启动脚本

echo "【Small-Cap Momentum Trader】"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python 3"
    echo "请先安装 Python 3.9+ 然后重试"
    exit 1
fi

# 显示 Python 版本
echo "✅ 已找到 Python:"
python3 --version
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 运行机械人
echo "🚀 启动交易机械人..."
echo ""

python3 run.py
