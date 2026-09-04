from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
import threading
import time
from datetime import datetime, timedelta
import requests

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

CHANNEL_ACCESS_TOKEN = "YNKog7hkVGIly0K8xwL0Gu7NlozQAAumN3SNqUqzg5YutUyTufgnAF1Sl23iJhWIy4luK6u+KmPFyc/XsZEvK7od/ZzZ0yBM5EBOL09qn10RV8FLwQvhBmZTdZb0ePOGZIA55TYkgQbFreP8jkFkGwdB04t89/1O/w1cDnyilFU="

def init_db():
    try:
        conn = sqlite3.connect('database.db', timeout=10)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT NOT NULL,
                message TEXT,
                image_path TEXT,
                post_time TEXT NOT NULL,
                status TEXT DEFAULT 'pending'
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database init error: {e}")

init_db()

def send_line_message(to_id, message, image_url=None):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
    }
    messages = []
    
    if image_url:
        messages.append({
            "type": "image",
            "originalContentUrl": image_url,
            "previewImageUrl": image_url
        })
        
    if message:
        messages.append({"type": "text", "text": message})
    
    data = {
        "to": to_id,
        "messages": messages
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        print(f"LINE API Status Code: {response.status_code}, Response: {response.text}")
        return response.json()
    except Exception as e:
        print(f"LINE API Request failed: {e}")
        return None

# ระบบเช็กเวลาแบบปลอดภัย ป้องกัน Thread ล่ม
def background_scheduler():
    print("Background scheduler started...")
    while True:
        try:
            time.sleep(15) # เช็กทุกๆ 15 วินาที
            init_db()
            conn = sqlite3.connect('database.db', timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT id, group_id, message, image_path, post_time FROM scheduled_posts WHERE status = 'pending'")
            posts = cursor.fetchall()
            conn.close()

            if posts:
                print(f"พบโพสต์ที่รอส่ง: {len(posts)} รายการ")

            now = datetime.utcnow() + timedelta(hours=7)
            
            for post in posts:
                post_id, group_id, message, image_path, post_time_str = post
                try:
                    # ทำความสะอาดรูปแบบเวลาให้รองรับทุกเคส
                    post_time_str = post_time_str.replace('T', ' ')
                    if len(post_time_str) == 16: # กรณีพิมพ์แบบ YYYY-MM-DD HH:MM
                        post_time = datetime.strptime(post_time_str, '%Y-%m-%d %H:%M')
                    else:
                        post_time = datetime.strptime(post_time_str[:16], '%Y-%m-%d %H:%M')
                    
                    if now >= post_time:
                        print(f"ถึงเวลาส่งโพสต์ ID {post_id} กำลังส่ง... (เวลาเป้าหมาย: {post_time}, เวลาปัจจุบัน: {now})")
                        
                        img_url = None
                        if image_path:
                            base_url = "https://camper-bot.onrender.com"
                            img_url = f"{base_url}/{image_path}"
                        
                        send_line_message(group_id, message, img_url)
                        
                        conn = sqlite3.connect('database.db', timeout=10)
                        cursor = conn.cursor()
                        cursor.execute("UPDATE scheduled_posts SET status = 'sent' WHERE id = ?", (post_id,))
                        conn.commit()
                        conn.close()
                        print(f"อัปเดตสถานะโพสต์ ID {post_id} เป็น sent สำเร็จ!")
                except Exception as ex:
                    print(f"เกิดข้อผิดพลาดในการประมวลผลโพสต์ ID {post_id}: {ex}")
        except Exception as e:
            print(f"Background worker loop error: {e}")

# เริ่มรัน Background Task แบบแยก Thread เดี่ยว
def start_background_task():
    t = threading.Thread(target=background_scheduler)
    t.daemon = True
    t.start()

start_background_task()

@app.route('/', methods=['GET', 'POST'])
def index():
    init_db()
    conn = sqlite3.connect('database.db', timeout=10)
    cursor = conn.cursor()
    
    if request.method == 'POST':
        group_id = request.form.get('group_id', 'C6a472edb8a62eba27b5c42c346492017')
        message = request.form.get('message')
        post_time = request.form.get('post_time')
        
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                filename = file.filename
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                image_path = file_path
        
        cursor.execute("""
            INSERT INTO scheduled_posts (group_id, message, image_path, post_time, status)
            VALUES (?, ?, ?, ?, 'pending')
        """, (group_id, message, image_path, post_time))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
        
    cursor.execute("SELECT id, group_id, message, post_time, status FROM scheduled_posts ORDER BY id DESC")
    posts = cursor.fetchall()
    conn.close()
    
    return render_template('index.html', posts=posts)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
