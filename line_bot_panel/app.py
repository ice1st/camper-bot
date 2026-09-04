from flask import Flask, render_template, request, abort, redirect, url_for
import sqlite3
import os
import requests

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ใส่ Channel Access Token ตัวเดิมของคุณตรงนี้
CHANNEL_ACCESS_TOKEN = "YNKog7hkVGIly0K8xwL0Gu7NlozQAAumN3SNqUqzg5YutUyTufgnAF1Sl23iJhWIy4luK6u+KmPFyc/XsZEvK7od/ZzZ0yBM5EBOL09qn10RV8FLwQvhBmZTdZb0ePOGZIA55TYkgQbFreP8jkFkGwdB04t89/1O/w1cDnyilFU="

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scheduled_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id TEXT,
            message TEXT,
            image_path TEXT,
            post_time TEXT,
            status TEXT DEFAULT 'pending'
        )
    ''')
    conn.commit()
    conn.close()

def send_line_message(to_id, message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
    }
    data = {
        "to": to_id,
        "messages": [{"type": "text", "text": message}]
    }
    requests.post(url, headers=headers, json=data)

# ฟังก์ชันรับ Webhook จาก LINE (เวลาใครพิมพ์อะไร หรือดึงบอทเข้ากลุ่ม)
@app.route('/webhook', methods=['POST'])
def webhook():
    body = request.get_json()
    if not body:
        return abort(400)
    
    events = body.get('events', [])
    for event in events:
        if event.get('type') == 'message':
            source = event.get('source', {})
            source_type = source.get('type')
            
            # ถ้าพิมพ์ในกลุ่ม หรือห้องแชต
            if source_type in ['group', 'room']:
                chat_id = source.get('groupId') or source.get('roomId')
                user_message = event.get('message', {}).get('text', '')
                
                # ถ้าพิมพ์คำว่า "id" หรือ "ไอดี" ให้บอทตอบ Group ID กลับทันที
                if user_message.lower() in ['id', 'ไอดี', 'group id']:
                    send_line_message(chat_id, f"📌 Group ID ของกลุ่มนี้คือ:\n{chat_id}")
                    
    return 'OK', 200

@app.route('/', methods=['GET', 'POST'])
def index():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    if request.method == 'POST':
        group_id = request.form.get('group_id')
        message = request.form.get('message')
        post_time = request.form.get('post_time')
        
        image_file = request.files.get('image')
        image_path = None
        
        if image_file and image_file.filename != '':
            image_filename = image_file.filename
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            image_file.save(image_path)
            image_path = image_path.replace('\\', '/')
            
        cursor.execute('''
            INSERT INTO scheduled_posts (group_id, message, image_path, post_time) 
            VALUES (?, ?, ?, ?)
        ''', (group_id, message, image_path, post_time))
        
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    
    cursor.execute('SELECT * FROM scheduled_posts ORDER BY id DESC')
    posts = cursor.fetchall()
    conn.close()
    
    return render_template('index.html', posts=posts)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)