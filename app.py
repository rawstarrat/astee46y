from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib, time, secrets, json, urllib.request

app = Flask(__name__)
CORS(app)

# === FIREBASE CONFIG ===
FIREBASE_DB_URL = "https://ellscary-default-rtdb.asia-southeast1.firebasedatabase.app"
FIREBASE_SECRET = "AIzaSyB-_79tsrLtie2pj9txZV9ORQci3sXzK40"

# === FUNGSI FIRESTORE/REALTIME ===
def firebase_get(path):
    url = f"{FIREBASE_DB_URL}/{path}.json?auth={FIREBASE_SECRET}"
    try:
        with urllib.request.urlopen(url) as res:
            return json.loads(res.read().decode())
    except:
        return None

def firebase_set(path, data):
    url = f"{FIREBASE_DB_URL}/{path}.json?auth={FIREBASE_SECRET}"
    req = urllib.request.Request(url, data=json.dumps(data).encode(), method="PUT")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read().decode())
    except Exception as e:
        return str(e)

# === GENERATE KEY & EXPIRED ===
def generate_key(username, role):
    return hashlib.sha256(f"{username}{time.time()}{secrets.token_hex(8)}".encode()).hexdigest()[:32]

def expired_date(day):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + day*86400))

# === LOGIN ===
@app.route('/login')
def login():
    username = request.args.get('username', '')
    password = request.args.get('password', '')
    users = firebase_get('users')
    if users:
        for uid, data in users.items():
            if data.get('username') == username and data.get('password') == password:
                session_key = generate_key(username, data.get('role'))
                session_data = {
                    'sessionKey': session_key,
                    'username': username,
                    'role': data.get('role')
                }
                firebase_set(f'sessions/{session_key}', session_data)
                return jsonify({'valid': True, 'sessionKey': session_key, 'username': username, 'role': data.get('role')})
    return jsonify({'valid': False, 'message': 'Username / password salah!'})

# === LIST USERS ===
@app.route('/listUsers')
def list_users():
    key = request.args.get('key', '')
    sess = firebase_get(f'sessions/{key}')
    if not sess:
        return jsonify({'valid': False, 'authorized': False, 'message': 'Session invalid!'})
    users = firebase_get('users')
    user_list = []
    if users:
        for uid, data in users.items():
            user_list.append({
                'username': data.get('username'),
                'role': data.get('role'),
                'expiredDate': data.get('expired_at'),
                'parent': data.get('parent', 'SYSTEM')
            })
    return jsonify({'valid': True, 'authorized': True, 'users': user_list})

# === ADD USER ===
@app.route('/userAdd')
def add_user():
    key = request.args.get('key', '')
    username = request.args.get('username', '')
    password = request.args.get('password', '')
    day = int(request.args.get('day', 0))
    role = request.args.get('role', 'member')

    sess = firebase_get(f'sessions/{key}')
    if not sess:
        return jsonify({'created': False, 'message': 'Session invalid!'})

    uid = hashlib.md5(username.encode()).hexdigest()[:16]
    firebase_set(f'users/{uid}', {
        'username': username,
        'password': password,
        'role': role,
        'status': 'active',
        'premium': role in ['premium', 'vip'],
        'vip': role == 'vip',
        'expired_at': expired_date(day),
        'parent': sess.get('username', 'SYSTEM')
    })
    return jsonify({'created': True, 'user': {'username': username, 'role': role, 'expiredDate': expired_date(day)}})

# === DELETE USER ===
@app.route('/deleteUser')
def delete_user():
    key = request.args.get('key', '')
    username = request.args.get('username', '')
    sess = firebase_get(f'sessions/{key}')
    if not sess:
        return jsonify({'deleted': False, 'message': 'Session invalid!'})

    users = firebase_get('users')
    if users:
        for uid, data in users.items():
            if data.get('username') == username:
                firebase_set(f'users/{uid}', None)
                return jsonify({'deleted': True, 'user': {'username': username}})
    return jsonify({'deleted': False, 'message': 'User tidak ditemukan!'})

if __name__ == '__main__':
    app.run(debug=True)