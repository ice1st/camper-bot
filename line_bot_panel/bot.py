import sqlite3
import requests
import time
from datetime import datetime
import os

CHANNEL_ACCESS_TOKEN = "YNKog7hkVGIly0K8xwL0Gu7NlozQAAumN3SNqUqzg5YutUyTufgnAF1Sl23iJhWIy4luK6u+KmPFyc/XsZEvK7od/ZzZ0yBM5EBOL09qn10RV8FLwQvhBmZTdZb0ePOGZIA55TYkgQbFreP8jkFkGwdB04t89/1O/w1cDnyilFU="

def send_line_message(to_id, message, image_path=None):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
    }
    
    messages = []
    
    # ถ้ามีรูปภาพแนบมาด้วย และไฟล์มีอยู่จริง
    if image_path and os.path.exists(image_path):
        # หมายเหตุ: LINE API บังคับว่าลิงก์รูปภาพต้องเป็น HTTPS ที่เข้าถึงได้จากภายนอก
        # หากรันในเครื่อง (Localhost) LINE จะมองไม่เห็นรูป เว้นแต่เราจะใช้ ngrok หรืออัปโหลดขึ้น Host สาธารณะ
        # แต่ถ้าทดสอบชั่วคราว เราสามารถแปลงหรือเช็กเงื่อนไขตรงนี้ได้ครับ
        pass

    # เพิ่มข้อความหลักลงไปก่อน
    if message:
        messages.append({"type": "text", "text": message})
        
    # หากมีรูปภาพ (ต้องใช้ URL จริงแบบ Public ที่ LINE โหลดได้)
    # เช่น ถ้า image_path ถูกเก็บเป็น static/uploads/... เราสามารถแปะลิงก์รูปภาพได้ถ้ามีโดเมน
    # แต่ตอนนี้ถ้ายังไม่ได้เปิด ngrok รูปอาจจะยังไม่แสดงผล LINE API บังคับ HTTPS URL ครับ
    
    data = {
        "to": to_id,
        "messages": messages
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

def check_and_send_posts():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, group_id, message, image_path, post_time FROM scheduled_posts WHERE status = 'pending'")
    posts = cursor.fetchall()
    
    now = datetime.now()
    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] กำลังตรวจสอบคิวโพสต์...")

    for post in posts:
        post_id, group_id, message, image_path, post_time_str = post
        
        try:
            if 'T' in post_time_str:
                post_time = datetime.strptime(post_time_str, '%Y-%m-%dT%H:%M')
            else:
                post_time = datetime.strptime(post_time_str, '%Y-%m-%d %H:%M')
            
            if now >= post_time:
                print(f" ถึงเวลาส่งโพสต์ ID {post_id} แล้ว กำลังส่ง...")
                result = send_line_message(group_id, message, image_path)
                
                cursor.execute("UPDATE scheduled_posts SET status = 'sent' WHERE id = ?", (post_id,))
                conn.commit()
                print(f" ส่งโพสต์ ID {post_id} สำเร็จ!")
            else:
                print(f" โพสต์ ID {post_id} ยังไม่ถึงเวลา (กำหนดส่ง: {post_time_str})")
                
        except Exception as e:
            print(f" เกิดข้อผิดพลาดกับโพสต์ ID {post_id}: {e}")
            
    conn.close()

if __name__ == "__main__":
    print("Camper Bot เริ่มทำงานและรอเช็กคิวโพสต์ตามเวลา...")
    while True:
        check_and_send_posts()
        time.sleep(10)