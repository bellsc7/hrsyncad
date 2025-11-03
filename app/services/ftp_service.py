import ftplib
import csv
import io
from datetime import datetime
from app_factory import db, get_asia_bangkok_time
from app.models.employee import Employee
from config import Config

def fetch_employees_from_ftp():
    try:
        with db.session.no_autoflush:
            ftp = ftplib.FTP(Config.FTP_HOST)
            ftp.login(Config.FTP_USER, Config.FTP_PASSWORD)
            ftp.set_pasv(True)  # Enable passive mode for better compatibility
            ftp.cwd(Config.FTP_PATH)
            
            files = ftp.nlst()
            
            for filename in files:
                if filename.endswith('.csv'):
                    file_data = io.BytesIO()
                    ftp.retrbinary(f"RETR {filename}", file_data.write)
                    file_data.seek(0)
                    
                    csv_reader = csv.DictReader(io.StringIO(file_data.read().decode('utf-8')))
                    
                    for row in csv_reader:
                        # Debug: แสดง employee_id ที่กำลังดำเนิน
                        print(f"Processing employee_id: {row['employeeid']}")
                        
                        # ตรวจสอบว่ามีพนักงานที่มี employee_id นี้อยู่แล้ว
                        employee = Employee.query.filter_by(employee_id=row['employeeid']).first()
                        
                        if not employee:
                            # สร้าง employee ใหม่
                            employee = Employee(employee_id=row['employeeid'])
                            print(f"Creating new employee with ID: {row['employeeid']}")
                        else:
                            # ตรวจสอบว่ามีการอัพเดตข้อมูลใน CSV (fname, lname)
                            has_update_data = any([row.get('fname'), row.get('lname')])
                            
                            if has_update_data:
                                print(f"Updating existing employee with ID: {row['employeeid']}")
                        
                        # อัพเดตข้อมูลจาก CSV สำหรับทั้งพนักงานใหม่และพนักงานเดิม
                        if row.get('fname'):
                            employee.fname = row.get('fname')
                        if row.get('lname'):
                            employee.lname = row.get('lname')
                        if row.get('phone'):
                            employee.phone = row.get('phone')
                        if row.get('department'):
                            employee.department = row.get('department')
                        if row.get('empPostionTdesc'):
                            employee.position = row.get('empPostionTdesc')
                        
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
                        
                        employee.last_updated = get_asia_bangkok_time()  # อัพเดตเวลาเป็น Asia/Bangkok
                        employee.ad_updated = False  # รีเซ็ตสถานะเพื่อให้อัพเดต AD ใหม่
                        
                        # ตรวจสอบว่าข้อมูลครบถ้วก่อนมีค่า null สำหรับ required fields
                        if not any([employee.fname, employee.lname]):
                            print(f"Skipping employee {row['employeeid']} - all required fields are null")
                            continue
                        
                        db.session.add(employee)
                
            db.session.commit()
            try:
                for filename in files:
                    ftp.rename(filename, f"processed/{filename}")
                    print(f"Successfully moved {filename} to processed folder")
            except Exception as rename_error:
                print(f"Failed to move {filename} to processed folder: {rename_error}")
                # Continue with other files even if rename fails
                
        ftp.quit()
        return True
    except Exception as e:
        print(f"Error fetching employees from FTP: {e}")
        db.session.rollback()
        return False