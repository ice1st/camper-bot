from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
import threading
import time
from datetime import datetime, timedelta
import requests

app = Flask(__name__)

# ใส่ Channel Access Token ของ LINE Bot คุณที่นี่
CHANNEL_ACCESS_TOKEN = "YNKog7hkVGIly0K8xwL0Gu7NlozQAAumN3SNqUqzg5YutUyTufgnAF1Sl23iJhWIy4luK6u+KmPFyc/XsZEvK7od/ZzZ0yBM5EBOL09qn10RV8FLwQvhBmZTdZb0ePOGZIA55TYkgQbFreP8jkFkGwdB04t89/1O/w1cDnyilFU="

# ฟังก์ชันส่งข้อความเข้า LINE
def send_line_message(to_id, message, image_path=None):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
    }
    messages = []
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

            # แปลงเวลาเซิร์ฟเวอร์ (UTC) ให้เป็นเวลาไทย (+7 ชั่วโมง)
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
                        send_line_message(group_id, message, image_path)
                        
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
        
        time.sleep(10) # เช็กทุกๆ 10 วินาที

# เริ่มต้นรันระบบเบื้องหลังคู่กับเว็บอัตโนมัติ
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
        
        cursor.execute("""
            INSERT INTO scheduled_posts (group_id, message, image_path, post_time, status)
            VALUES (?, ?, ?, ?, 'pending')
        """, (group_id, message, None, post_time))
        conn.commit()
        return redirect(url_for('index'))
        
    cursor.execute("SELECT id, group_id, message, post_time, status FROM scheduled_posts ORDER BY id DESC")
    posts = cursor.fetchall()
    conn.close()
    
    return render_template('index.html', posts=posts)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
