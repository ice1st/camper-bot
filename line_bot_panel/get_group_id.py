import requests

CHANNEL_ACCESS_TOKEN = "YNKog7hkVGIly0K8xwL0Gu7NlozQAAumN3SNqUqzg5YutUyTufgnAF1Sl23iJhWIy4luK6u+KmPFyc/XsZEvK7od/ZzZ0yBM5EBOL09qn10RV8FLwQvhBmZTdZb0ePOGZIA55TYkgQbFreP8jkFkGwdB04t89/1O/w1cDnyilFU="

def get_bot_groups():
    # LINE Messaging API สำหรับดึงรายชื่อกลุ่มที่บอทเข้าร่วม (ต้องเป็นเวอร์ชันที่รองรับ หรือใช้ endpoint ทดสอบ)
    # หรือใช้วิธีดึงผ่าน User ID / Webhook ฝั่ง LINE OA
    print("กำลังตรวจสอบกลุ่มที่บอทอยู่...")

if __name__ == "__main__":
    print("🔍 วิธีเช็ก Group ID ง่ายๆ แบบไม่ต้องพึ่ง ngrok:")
    print("1. ให้ลองพิมพ์ข้อความอะไรก็ได้ในกลุ่ม LINE ที่มีบอทอยู่")
    print("2. หรือเราสามารถใช้ระบบ Log ง่ายๆ ใน bot.py เพื่อดู source.groupId ได้เลยครับ")