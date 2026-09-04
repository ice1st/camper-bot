from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
import threading
import time
from datetime import datetime, timedelta
import requests

app = Flask(__name__)

# กำหนดโฟลเดอร์สำหรับเก็บรูปที่อัปโหลด
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ใส่ Channel Access Token ของ LINE Bot คุณที่นี่
CHANNEL_ACCESS_TOKEN = "YNKog7hkVGIly0K8xwL0Gu7NlozQAAumN3SNqUqzg5YutUyTufgnAF1Sl23iJhWIy4luK6u+KmPFyc/XsZEvK7od/ZzZ0yBM5EBOL09qn10RV8FLwQvhBmZTdZb0ePOGZIA55TYkgQbFreP8jkFkGwdB04t89/1O/w1cDnyilFU="

# ฟังก์ชันส่งข้อความและรูปภาพเข้า LINE
def send_line_message(to_id, message, image_url=None):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
    }
    messages = []
    
    # ถ้ามีรูปภาพ ให้แนบประเภท image ไปด้วย (ต้องเป็นลิงก์ URL จริง)
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
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# ฟังก์ชันเบื้องหลังคอยเช็กเวลาส่งโพสต์อัตโนมัติ (เทียบเวลาไทย UTC+7)
def background_scheduler():
    while True:
        try:
            print("กำลังตรวจสอบคิวโพสต์...")
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, group_id, message, image_path, post_time FROM scheduled_posts WHERE status = 'pending'")
            posts = cursor.fetchall()
            conn.close()

            now = datetime.utcnow() + timedelta(hours=7)
            
            for post in posts:
                post_id, group_id, message, image_path, post_time_str = post
                try:
                    if 'T' in post_time_str:
                        post_time = datetime.strptime(post_time_str, '%Y-%m-%dT%H:%M')
                    else:
                        post_time = datetime.strptime(post_time_str, '%Y-%m-%d %H:%M')
                    
                    if now >= post_time:
                        print(f"ถึงเวลาส่งโพสต์ ID {post_id} กำลังส่ง...")
                        
                        # แปลง path รูปให้เป็น Public URL ของ Render
                        img_url = None
                        if image_path:
                            # เปลี่ยน URL ตรงนี้ให้ตรงกับชื่อเว็บ Render ของคุณจริงๆ
                            base_url = "https://camper-bot.onrender.com"
                            img_url = f"{base_url}/{image_path}"
                        
                        send_line_message(group_id, message, img_url)
                        
                        conn = sqlite3.connect('database.db')
                        cursor = conn.cursor()
                        cursor.execute("UPDATE scheduled_posts SET status = 'sent' WHERE id = ?", (post_id,))
                        conn.commit()
                        conn.close()
                        print(f"ส่งโพสต์ ID {post_id} สำเร็จ!")
                except Exception as e:
                    print(f"เกิดข้อผิดพลาดกับโพสต์ ID {post_id}: {e}")
        except Exception as e:
            print(f"Background worker error: {e}")
        
        time.sleep(10)

def start_background_task():
    t = threading.Thread(target=background_scheduler)
    t.daemon = True
    t.start()

start_background_task()

# หน้าเว็บไซต์หลัก
@app.route('/', methods=['GET', 'POST'])
def index():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    if request.method == 'POST':
        group_id = request.form.get('group_id', 'C6a472edb8a62eba27b5c42c346492017')
        message = request.form.get('message')
        post_time = request.form.get('post_time')
        
        # จัดการอัปโหลดไฟล์รูปภาพ
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                filename = file.filename
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                image_path = file_path # บันทึก path เช่น static/uploads/xxx.jpg
        
        cursor.execute("""
            INSERT INTO scheduled_posts (group_id, message, image_path, post_time, status)
            VALUES (?, ?, ?, ?, 'pending')
        """, (group_id, message, image_path, post_time))
        conn.commit()
        return redirect(url_for('index'))
        
    cursor.execute("SELECT id, group_id, message, post_time, status FROM scheduled_posts ORDER BY id DESC")
    posts = cursor.fetchall()
    conn.close()
    
    return render_template('index.html', posts=posts)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
