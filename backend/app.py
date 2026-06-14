from flask import Flask, request, jsonify, g
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime

app = Flask(__name__, static_folder='..', static_url_path='')
CORS(app)

# 首页重定向
@app.route('/')
def root():
    return app.send_static_file('index.html')

DB_PATH = os.path.join(os.path.dirname(__file__), 'flowers.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db = get_db()
        db.executescript('''
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                phone TEXT NOT NULL,
                school TEXT NOT NULL,
                flower_name TEXT NOT NULL,
                flower_price INTEGER NOT NULL,
                count INTEGER NOT NULL DEFAULT 1,
                total INTEGER NOT NULL,
                time TEXT NOT NULL,
                name TEXT DEFAULT '未填写',
                message TEXT DEFAULT '无',
                created_at TEXT NOT NULL,
                taken INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS phones (
                phone TEXT PRIMARY KEY
            );
        ''')
        db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# ==================== API ====================

# 提交订单
@app.route('/api/order', methods=['POST'])
def create_order():
    data = request.get_json()
    required = ['id', 'phone', 'school', 'flowerName', 'flowerPrice', 'count', 'total', 'time']
    for k in required:
        if k not in data:
            return jsonify({'error': f'缺少字段 {k}'}), 400

    db = get_db()
    db.execute(
        'INSERT INTO orders (id, phone, school, flower_name, flower_price, count, total, time, name, message, created_at, taken) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            data['id'],
            data['phone'],
            data['school'],
            data['flowerName'],
            data['flowerPrice'],
            data['count'],
            data['total'],
            data['time'],
            data.get('name', '未填写'),
            data.get('message', '无'),
            datetime.now().strftime('%Y/%m/%d %H:%M'),
            0
        )
    )
    # 记录手机号
    db.execute('INSERT OR IGNORE INTO phones (phone) VALUES (?)', (data['phone'],))
    db.commit()
    return jsonify({'ok': True})

# 获取所有订单（管理后台用）
@app.route('/api/orders', methods=['GET'])
def get_orders():
    db = get_db()
    rows = db.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall()
    return jsonify([dict(r) for r in rows])

# 获取公开订单通知（最近 12 条，脱敏）
@app.route('/api/notices', methods=['GET'])
def get_notices():
    db = get_db()
    rows = db.execute('SELECT id, phone, flower_name, count, created_at FROM orders ORDER BY created_at DESC LIMIT 12').fetchall()
    notices = []
    for r in rows:
        phone = r['phone']
        masked = phone[:3] + '****' + phone[-4:] if len(phone) == 11 else phone
        notices.append({
            'id': r['id'],
            'phone': masked,
            'flowerName': r['flower_name'],
            'count': r['count'],
        })
    return jsonify(notices)

# 标记取花
@app.route('/api/order/<order_id>/take', methods=['POST'])
def take_order(order_id):
    db = get_db()
    db.execute('UPDATE orders SET taken = 1 WHERE id = ?', (order_id,))
    db.commit()
    return jsonify({'ok': True})

# 删除订单
@app.route('/api/order/<order_id>', methods=['DELETE'])
def delete_order(order_id):
    db = get_db()
    db.execute('DELETE FROM orders WHERE id = ?', (order_id,))
    db.commit()
    return jsonify({'ok': True})

@app.route('/admin')
def admin():
    return app.send_static_file('admin.html')

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 8899))
    print(f'🚀 中考花坊 running on http://0.0.0.0:{port}')
    app.run(host='0.0.0.0', port=port, debug=False)
