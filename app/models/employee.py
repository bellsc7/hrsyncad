from app_factory import db, get_asia_bangkok_time
from datetime import datetime

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(20), unique=True, nullable=False)
    fname = db.Column(db.String(64), nullable=True)  # อนุญาให้เป็น nullable=True เพื่อรับข้อมูลที่อาจมีค่าว่าง
    lname = db.Column(db.String(64), nullable=True)  # อนุญาให้เป็น nullable=True เพื่อรับข้อมูลที่อาจมีค่าว่าง
    phone = db.Column(db.String(20))
    department = db.Column(db.String(64))
    position = db.Column(db.String(64))
    start_date = db.Column(db.Date)
    status = db.Column(db.String(20))
    last_updated = db.Column(db.DateTime, default=get_asia_bangkok_time, onupdate=get_asia_bangkok_time)
    ad_updated = db.Column(db.Boolean, default=False)
    resigndate = db.Column(db.Date, nullable=True)  # วันที่ลาออก
    account_expires_date = db.Column(db.Date, nullable=True)  # วันที่จะปิดใช้งานบน AD