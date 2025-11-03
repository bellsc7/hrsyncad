import requests
from app_factory import db, get_asia_bangkok_time
from app.models.employee import Employee
from config import Config
from datetime import datetime

def convert_date_format(date_str):
    """
    แปลงวันที่ได้รับจาก API หรือ FTP และ MyHR API
    รับเป็นปี พ.ศ. และแปลงเป็น ค.ศ. สำหรับเก็บในฐานข้อมูล
    """
    if not date_str:
        return None
    
    try:
        # แปลง string เป็น datetime object
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        # ถ้าเป็นปี พ.ศ. (year > 2500) ให้แปลงเป็น ค.ศ.
        if date_obj.year > 2500:
            buddhist_year = date_obj.year
            gregorian_year = buddhist_year - 543
            date_obj = date_obj.replace(year=gregorian_year)
        return date_obj.date()
    except (ValueError, TypeError):
        return None

def fetch_employees_from_api():
    try:
        headers = {'Authorization': f'Bearer {Config.MYHR_API_KEY}'}
        response = requests.get(Config.MYHR_API_URL, headers=headers, timeout=30)
        response.raise_for_status()
        
        employees_data = response.json()
        
        for emp_data in employees_data:
            employee = Employee.query.filter_by(employee_id=emp_data['employeeid']).first()
            
            if not employee:
                employee = Employee(employee_id=emp_data['employeeid'])
            
            employee.fname = emp_data.get('fname')
            employee.lname = emp_data.get('lname')
            employee.phone = emp_data.get('phone')
            employee.department = emp_data.get('department')
            employee.position = emp_data.get('empPostionTdesc')
            employee.start_date = convert_date_format(emp_data.get('start_date'))
            employee.status = emp_data.get('status')
            
            # แปลงวันที่ลาออก (รับเป็นปี พ.ศ.)
            employee.resigndate = convert_date_format(emp_data.get('resigndate'))
            
            # แปลงวันที่หมดอายุบัญชี (รับเป็นปี พ.ศ.)
            if emp_data.get('resigndate'):
                # ถ้ามีวันที่ลาออก ให้ตั้งค่า account_expires_date อัตโนมัติเป็นวันเดียวกับ resigndate
                employee.account_expires_date = employee.resigndate
            elif emp_data.get('account_expires_date'):
                # ถ้าไม่มี resigndate แต่มี account_expires_date ให้ใช้ค่านั้น
                employee.account_expires_date = convert_date_format(emp_data.get('account_expires_date'))
            else:
                # ถ้าไม่มีทั้งสองอย่างให้เป็น None
                employee.account_expires_date = None
                
            employee.last_updated = get_asia_bangkok_time()  # อัพเดตเวลาเป็น Asia/Bangkok
            employee.ad_updated = False # รีเซ็ตสถานะเพื่อให้อัพเดต AD ใหม่
            
            db.session.add(employee)
        
        db.session.commit()
        return True
    except Exception as e:
        print(f"Error fetching employees from API: {e}")
        db.session.rollback()
        return False