"""
【Small-Cap Momentum Bot】Webhook 接收器
接收來自 TradingView 的實時信號，調用進場邏輯
"""
from flask import Flask, request, jsonify
from datetime import datetime
import json
import threading
import time

from utils.logger import get_logger

log = get_logger("webhook_receiver")

app = Flask(__name__)

# 全局引用 - 會由主程序設置
trading_engine = None


@app.route('/webhook/tradingview', methods=['POST'])
def receive_tradingview_signal():
    """接收 TradingView Webhook 信號"""
    try:
        data = request.get_json()

        if not data:
            log.warning("收到空的 webhook 請求")
            return jsonify({"status": "error", "message": "Empty payload"}), 400

        log.info(f"📩 收到 TradingView 信號: {data}")

        # 解析 TradingView 信號格式
        # 格式: "SYMBOL|ENTRY|PRICE|GAP=X%|RVOL=X.Xx|VOL=X"
        message = data.get("message", "")

        if "ENTRY" in message:
            parsed = parse_entry_signal(message)
            if parsed:
                log.info(f"✅ 解析成功: {parsed}")
                # 調用交易引擎的進場函數
                if trading_engine:
                    threading.Thread(
                        target=execute_entry_signal,
                        args=(parsed,),
                        daemon=True
                    ).start()
                    return jsonify({"status": "success", "message": "Signal processed"}), 200
                else:
                    log.error("交易引擎未初始化")
                    return jsonify({"status": "error", "message": "Trading engine not initialized"}), 500

        return jsonify({"status": "warning", "message": "Unknown signal type"}), 200

    except Exception as e:
        log.error(f"Webhook 處理出錯: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/webhook/health', methods=['GET'])
def health_check():
    """健康檢查"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "service": "Small-Cap Momentum Bot Webhook Receiver"
    }), 200


@app.route('/webhook/status', methods=['GET'])
def status():
    """獲取交易機械人狀態"""
    if not trading_engine:
        return jsonify({"status": "offline"}), 503

    return jsonify({
        "status": "online",
        "time_status": trading_engine.get_time_status() if hasattr(trading_engine, 'get_time_status') else "unknown",
        "positions": len(trading_engine.watchlist) if hasattr(trading_engine, 'watchlist') else 0,
        "timestamp": datetime.now().isoformat()
    }), 200


def parse_entry_signal(message: str) -> dict:
    """解析 TradingView 進場信號

    格式: "SYMBOL|ENTRY|PRICE|GAP=X%|RVOL=X.Xx|VOL=X"
    例: "UPST|ENTRY|15.50|GAP=6.23%|RVOL=3.45x|VOL=2500000"
    """
    try:
        parts = message.split("|")
        if len(parts) < 3:
            return None

        symbol = parts[0].strip()
        signal_type = parts[1].strip()
        price = float(parts[2].strip())

        # 解析附加參數
        gap_pct = 0
        rvol = 0
        volume = 0

        for part in parts[3:]:
            if "GAP=" in part:
                gap_str = part.replace("GAP=", "").replace("%", "").strip()
                gap_pct = float(gap_str)
            elif "RVOL=" in part:
                rvol_str = part.replace("RVOL=", "").replace("x", "").strip()
                rvol = float(rvol_str)
            elif "VOL=" in part:
                vol_str = part.replace("VOL=", "").strip()
                volume = int(vol_str)

        return {
            "symbol": symbol,
            "signal_type": signal_type,
            "entry_price": price,
            "gap_pct": gap_pct,
            "rvol": rvol,
            "volume": volume,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        log.error(f"解析信號失敗: {e}")
        return None


def execute_entry_signal(signal: dict):
    """執行進場信號"""
    try:
        symbol = signal["symbol"]
        entry_price = signal["entry_price"]

        log.info(f"🎯 執行進場: {symbol} @ ${entry_price:.2f}")
        log.info(f"   Gap: {signal['gap_pct']:.1f}% | RVOL: {signal['rvol']:.1f}x | Vol: {signal['volume']:,}")

        # 計算止蝕價格（簡單方法：進場價格 - 0.50）
        stop_price = entry_price - 0.50

        # 調用交易引擎的進場函數
        if hasattr(trading_engine, 'execute_entry'):
            contract = trading_engine.ibkr.make_stock(symbol)
            try:
                contract = trading_engine.ibkr.qualify_contract(contract)
                success = trading_engine.execute_entry(symbol, contract, entry_price, stop_price)

                if success:
                    log.info(f"✅ 進場成功: {symbol}")
                else:
                    log.warning(f"⚠️ 進場失敗: {symbol}")
            except Exception as e:
                log.error(f"合約確認失敗: {e}")

    except Exception as e:
        log.error(f"執行進場信號時出錯: {e}")


def start_webhook_server(host: str = "127.0.0.1", port: int = 5000, engine=None):
    """啟動 Webhook 服務器（在後台線程中）"""
    global trading_engine
    trading_engine = engine

    log.info(f"🚀 啟動 Webhook 服務器 {host}:{port}")
    log.info(f"TradingView Alert Webhook URL: http://{host}:{port}/webhook/tradingview")

    # 在後台線程中運行 Flask
    def run_server():
        app.run(host=host, port=port, debug=False, use_reloader=False)

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # 等待服務器啟動
    time.sleep(2)
    log.info("✅ Webhook 服務器已啟動")

    return server_thread


if __name__ == "__main__":
    # 直接運行此檔案用於測試
    log.info("Webhook 服務器正在運行... (測試模式)")
    log.info("訪問: http://127.0.0.1:5000/webhook/health")
    app.run(host="127.0.0.1", port=5000, debug=True)
