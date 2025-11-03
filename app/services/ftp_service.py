import ftplib
import csv
import io
from datetime import datetime
from app_factory import db, get_asia_bangkok_time
from app.models.employee import Employee
from config import Config

def fetch_employees_from_ftp():
    try:
        ftp = ftplib.FTP(Config.FTP_HOST)
        ftp.login(Config.FTP_USER, Config.FTP_PASSWORD)
        ftp.cwd(Config.FTP_PATH)
        
        files = ftp.nlst()
        
        for filename in files:
            if filename.endswith('.csv'):
                file_data = io.BytesIO()
                ftp.retrbinary(f"RETR {filename}", file_data.write)
                file_data.seek(0)
                
                csv_reader = csv.DictReader(io.StringIO(file_data.read().decode('utf-8')))
                
                for row in csv_reader:
                    employee = Employee.query.filter_by(employee_id=row['employee_id']).first()
                    
                    if not employee:
                        employee = Employee(employee_id=row['employee_id'])
                    
                    employee.fname = row.get('fname')
                    employee.lname = row.get('lname')
                    employee.email = row.get('email')
                    employee.phone = row.get('phone')
                    employee.department = row.get('department')
                    employee.position = row.get('position')
                    
                    # แปลงวันที่เริ่มงาน (รับเป็นปี พ.ศ.)
                    try:
                        if row.get('start_date'):
                            # แปลงจาก พ.ศ. เป็น ค.ศ. สำหรับเก็บในฐานข้อมูล
                            date_obj = datetime.strptime(row.get('start_date'), '%Y-%m-%d')
                            if date_obj.year > 2500:  # ถ้าเป็นปี พ.ศ.
                                buddhist_year = date_obj.year
                                gregorian_year = buddhist_year - 543
                                date_obj = date_obj.replace(year=gregorian_year)
                            employee.start_date = date_obj.date()
                        else:
                            employee.start_date = None
                    except (ValueError, TypeError):
                        employee.start_date = None
                    
                    employee.status = row.get('status')
                    
                    # แปลงวันที่ลาออก (รับเป็นปี พ.ศ.)
                    try:
                        if row.get('resigndate'):
                            # แปลงจาก พ.ศ. เป็น ค.ศ. สำหรับเก็บในฐานข้อมูล
                            date_obj = datetime.strptime(row.get('resigndate'), '%Y-%m-%d')
                            if date_obj.year > 2500:  # ถ้าเป็นปี พ.ศ.
                                buddhist_year = date_obj.year
                                gregorian_year = buddhist_year - 543
                                date_obj = date_obj.replace(year=gregorian_year)
                            employee.resigndate = date_obj.date()
                            # ถ้ามีวันที่ลาออก ให้ตั้งค่า account_expires_date อัตโนมัติเป็นวันเดียวกับ resigndate
                            employee.account_expires_date = employee.resigndate
                        else:
                            employee.resigndate = None
                    except (ValueError, TypeError):
                        employee.resigndate = None
                    
                    # แปลงวันที่หมดอายุบัญชี (รับเป็นปี พ.ศ.)
                    try:
                        # ตรวจสอบว่ามีการกำหนด account_expires_date ในไฟล์ CSV และไม่มี resigndate
                        if row.get('account_expires_date') and not employee.resigndate:
                            # แปลงจาก พ.ศ. เป็น ค.ศ. สำหรับเก็บในฐานข้อมูล
                            date_obj = datetime.strptime(row.get('account_expires_date'), '%Y-%m-%d')
                            if date_obj.year > 2500:  # ถ้าเป็นปี พ.ศ.
                                buddhist_year = date_obj.year
                                gregorian_year = buddhist_year - 543
                                date_obj = date_obj.replace(year=gregorian_year)
                            employee.account_expires_date = date_obj.date()
                        # ถ้าไม่มี account_expires_date ใน CSV และไม่มี resigndate ให้เป็น None
                        elif not row.get('account_expires_date') and not employee.resigndate:
                            employee.account_expires_date = None
                    except (ValueError, TypeError):
                        # ถ้ามี error แต่มี resigndate ให้คงค่า account_expires_date ที่ตั้งจาก resigndate ไว้
                        if not employee.resigndate:
                            employee.account_expires_date = None
                    
                    employee.ad_updated = False # รีเซ็ตสถานะเพื่อให้อัพเดต AD ใหม่
                    
                    db.session.add(employee)
                
                db.session.commit()
                ftp.rename(filename, f"processed/{filename}")
        
        ftp.quit()
        return True
    except Exception as e:
        print(f"Error fetching employees from FTP: {e}")
        db.session.rollback()
        return False