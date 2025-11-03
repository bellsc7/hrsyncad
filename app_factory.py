from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from datetime import datetime, timezone, timedelta

# สร้างอ็อบเจกต์ฐานข้อมูลและการจัดการการล็อกอิน
db = SQLAlchemy()
login_manager = LoginManager()

def get_asia_bangkok_time():
    """
    ฟังก์ชันนี้ใช้สำหรับดึงเวลาปัจจุบันในเขตเวลา Asia/Bangkok (UTC+7)
    :return: datetime object ของเวลาปัจจุบันในเขตเวลา Asia/Bangkok
    """
    # ดึงเวลา UTC ปัจจุบัน
    utc_now = datetime.now(timezone.utc)
    
    # แปลงเป็นเวลา Asia/Bangkok (UTC+7) โดยการบวก 7 ชั่วโมง
    bangkok_offset = timedelta(hours=7)
    bangkok_now = utc_now + bangkok_offset
    
    # คืนค่าเป็น datetime โดยไม่รวม timezone information
    return bangkok_now.replace(tzinfo=None)

def create_app(config_class='config.Config'):
    """
    Application factory pattern.
    Creates and configures the Flask application.
    """
    # สร้างแอปพลิเคชัน Flask
    app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
    app.config.from_object(config_class)
    
    # เริ่มต้นส่วนขยายต่างๆ
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    # ฟังก์ชันสำหรับสร้างตารางและข้อมูลเริ่มต้น
    def init_database():
        with app.app_context():
            # Import models ภายใน app context เพื่อหลีกเลี่ยง circular import
            from app.models import user, employee, sync_history
            
            # สร้างตารางทั้งหมดที่กำหนดไว้ใน models
            db.create_all()
            
            # สร้าง user admin ถ้ายังไม่มี (ใช้ try-except เพื่อความปลอดภัย)
            try:
                if not user.User.query.filter_by(username='admin').first():
                    admin_user = user.User(username='admin')
                    admin_user.set_password('admin123') # รหัสผ่านเริ่มต้น
                    db.session.add(admin_user)
                    db.session.commit()
                    print("Admin user created successfully.")
                else:
                    print("Admin user already exists.")
            except Exception as e:
                print(f"Error creating admin user: {e}")
                db.session.rollback()
    
    # ลงทะเบียน Blueprint สำหรับ routes
    from app.routes import auth, api, main
    app.register_blueprint(auth.bp)
    app.register_blueprint(api.bp, url_prefix='/api')
    app.register_blueprint(main.bp)
    
    # เรียกใช้ฟังก์ชันสร้างฐานข้อมูล
    init_database()
    
    return app