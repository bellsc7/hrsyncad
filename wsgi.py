from app_factory import create_app

# สร้าง instance ของแอปพลิเคชัน
# ส่งชื่อ config class ที่ถูกต้องไปยัง create_app
app = create_app('config.Config')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)