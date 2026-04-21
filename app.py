import os
import json
import time
import requests
from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)

SHOPIFY_SECRET = os.environ.get('SHOPIFY_SECRET', '')
ORDER_SITE_URL = os.environ.get('ORDER_SITE_URL', 'https://ec-luft.com/aec/user/')
ORDER_SITE_ID = os.environ.get('ORDER_SITE_ID', '')
ORDER_SITE_PASS = os.environ.get('ORDER_SITE_PASS', '')
LINE_TOKEN = os.environ.get('LINE_TOKEN', '')

PRODUCT_MAP = {
    'エルジューダ フリッズフィクサー エマルジョン＋': '115341',
}

def send_line_notify(message):
    if not LINE_TOKEN:
        print(f"LINE通知（トークン未設定）: {message}")
        return
    url = 'https://notify-api.line.me/api/notify'
    headers = {'Authorization': f'Bearer {LINE_TOKEN}'}
    data = {'message': message}
    try:
        requests.post(url, headers=headers, data=data)
    except Exception as e:
        print(f"LINE通知エラー: {e}")

def place_order(product_code, quantity, product_name):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(ORDER_SITE_URL)
            page.wait_for_load_state('networkidle')
            page.fill('input[name="id"], input[type="text"]', ORDER_SITE_ID)
            page.fill('input[name="password"], input[type="password"]', ORDER_SITE_PASS)
            page.click('button[type="submit"], input[type="submit"]')
            page.wait_for_load_state('networkidle')
            send_line_notify(f"✅ 発注完了\n商品: {product_name}\n数量: {quantity}")
            return True
        except Exception as e:
            send_line_notify(f"❌ 発注エラー\n商品: {product_name}\nエラー: {str(e)}")
            return False
        finally:
            browser.close()

@app.route('/webhook/shopify', methods=['POST'])
def shopify_webhook():
    try:
        data = request.get_json()
        order_id = data.get('id', 'unknown')
        line_items = data.get('line_items', [])
        send_line_notify(f"📦 新規注文受信\n注文番号: #{order_id}")
        for item in line_items:
            sku = item.get('sku', '')
            quantity = item.get('quantity', 1)
            product_name = item.get('name', '不明')
            if sku in PRODUCT_MAP:
                place_order(PRODUCT_MAP[sku], quantity, product_name)
            else:
                send_line_notify(f"⚠️ 未登録商品\n{product_name}\nSKU: {sku}")
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        send_line_notify(f"❌ システムエラー\n{str(e)}")
        return jsonify({'status': 'error'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'running', 'message': 'remente自動発注システム稼働中'}), 200

@app.route('/', methods=['GET'])
def index():
    return jsonify({'system': 'remente自動発注システム', 'status': '稼働中'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
