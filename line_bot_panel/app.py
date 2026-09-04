from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import sqlite3
import os
import threading
import time
from datetime import datetime, timedelta
import requests

app = Flask(__name__)

# ใช้ Railway Volume ที่ mount ไว้ที่ /app/data เพื่อความปลอดภัย ข้อมูลไม่หาย 100%
DATA_DIR = '/app/data'
if not os.path.exists(DATA_DIR):
    DATA_DIR = '.' # Fallback สำหรับรันเทสบนเครื่อง Local

DB_PATH = os.path.join(DATA_DIR, 'database.db')
UPLOAD_FOLDER = os.path.join(DATA_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

CHANNEL_ACCESS_TOKEN = "YNKog7hkVGIly0K8xwL0Gu7NlozQAAumN3SNqUqzg5YutUyTufgnAF1Sl23iJhWIy4luK6u+KmPFyc/XsZEvK7od/ZzZ0yBM5EBOL09qn10RV8FLwQvhBmZTdZb0ePOGZIA55TYkgQbFreP8jkFkGwdB04t89/1O/w1cDnyilFU="
RAILWAY_DOMAIN = "https://camper-bot-production.up.railway.app"

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()
        # ตารางเก็บคิวโพสต์
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
        # ตารางเก็บคลังรูปภาพ
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gallery (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                uploaded_at TEXT NOT NULL
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
            conn = sqlite3.connect(DB_PATH, timeout=10)
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
                    post_time_str = post_time_str.replace('T', ' ')
                    if len(post_time_str) == 16:
                        post_time = datetime.strptime(post_time_str, '%Y-%m-%d %H:%M')
                    else:
                        post_time = datetime.strptime(post_time_str[:16], '%Y-%m-%d %H:%M')
                    
                    if now >= post_time:
                        print(f"ถึงเวลาส่งโพสต์ ID {post_id} กำลังส่ง...")
                        
                        img_url = None
                        if image_path:
                            filename = os.path.basename(image_path)
                            img_url = f"{RAILWAY_DOMAIN}/uploads/{filename}"
                        
                        send_line_message(group_id, message, img_url)
                        
                        conn = sqlite3.connect(DB_PATH, timeout=10)
                        cursor = conn.cursor()
                        cursor.execute("UPDATE scheduled_posts SET status = 'sent' WHERE id = ?", (post_id,))
                        conn.commit()
                        conn.close()
                        print(f"อัปเดตสถานะโพสต์ ID {post_id} เป็น sent สำเร็จ!")
                except Exception as ex:
                    print(f"เกิดข้อผิดพลาดในการประมวลผลโพสต์ ID {post_id}: {ex}")
        except Exception as e:
            print(f"Background worker loop error: {e}")

def start_background_task():
    t = threading.Thread(target=background_scheduler)
    t.daemon = True
    t.start()

start_background_task()

# Route สำหรับดึงรูปภาพจาก Volume มาแสดงผล
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/', methods=['GET', 'POST'])
def index():
    init_db()
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()
    
    if request.method == 'POST':
        action = request.form.get('action', 'schedule')
        
        # 1. อัปโหลดรูปเข้าคลังภาพอย่างเดียว
        if action == 'upload_gallery':
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename != '':
                    filename = f"{int(time.time())}_{file.filename}"
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(file_path)
                    
                    cursor.execute("INSERT INTO gallery (filename, uploaded_at) VALUES (?, datetime('now', '+7 hours'))", (filename,))
                    conn.commit()
            conn.close()
            return redirect(url_for('index'))
            
        # 2. ตั้งเวลาโพสต์ (เลือกรูปจากคลัง หรืออัปโหลดใหม่)
        elif action == 'schedule':
            group_id = request.form.get('group_id', 'C6a472edb8a62eba27b5c42c346492017')
            message = request.form.get('message')
            post_time = request.form.get('post_time')
            
            image_filename = request.form.get('selected_gallery_image') # รูปที่เลือกจากคลัง
            
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename != '':
                    filename = f"{int(time.time())}_{file.filename}"
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(file_path)
                    image_filename = filename
                    cursor.execute("INSERT INTO gallery (filename, uploaded_at) VALUES (?, datetime('now', '+7 hours'))", (filename,))

            cursor.execute("""
                INSERT INTO scheduled_posts (group_id, message, image_path, post_time, status)
                VALUES (?, ?, ?, ?, 'pending')
            """, (group_id, message, image_filename, post_time))
            conn.commit()
            conn.close()
            return redirect(url_for('index'))
            
    cursor.execute("SELECT id, group_id, message, image_path, post_time, status FROM scheduled_posts ORDER BY id DESC")
    posts = cursor.fetchall()
    
    cursor.execute("SELECT id, filename, uploaded_at FROM gallery ORDER BY id DESC")
    gallery_images = cursor.fetchall()
    
    conn.close()
    
    return render_template('index.html', posts=posts, gallery_images=gallery_images)

# Route สำหรับลบรูปภาพออกจากคลังและลบไฟล์จริง
@app.route('/delete-image/<int:img_id>', methods=['POST'])
def delete_image(img_id):
    init_db()
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()
    
    cursor.execute("SELECT filename FROM gallery WHERE id = ?", (img_id,))
    row = cursor.fetchone()
    if row:
        filename = row[0]
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Error deleting file: {e}")
                
        cursor.execute("DELETE FROM gallery WHERE id = ?", (img_id,))
        conn.commit()
        
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
