import json # <-- เพิ่ม import json
from app.models.sync_history import SyncHistory
from ldap3 import Server, Connection, ALL, MODIFY_REPLACE
from app_factory import db, get_asia_bangkok_time
from app.models.employee import Employee
from config import Config
from datetime import datetime, timezone, timedelta

def convert_ce_to_ad_filetime(year_ce, month, day, hour, minute, second, timezone_offset_hours):
    """
    แปลงวันที่เวลาในรูปแบบ ค.ศ. และ Time Zone Offset เป็นค่า accountExpires (FILETIME) ของ AD
    
    :param year_ce: ปี ค.ศ. (เช่น 2025)
    :param month: เดือน (1-12)
    :param day: วันที่ (1-31)
    :param hour: ชั่วโมง (0-23)
    :param minute: นาที (0-59)
    :param second: วินาที (0-59)
    :param timezone_offset_hours: ผลต่างเขตเวลาจาก UTC (เช่น +7 สำหรับ GMT+7)
    :return: ค่า Long Integer ของ accountExpires (FILETIME)
    """
    
    # --- 1. กำหนดค่าคงที่ ---
    WINDOWS_EPOCH = datetime(1601, 1, 1, tzinfo=timezone.utc)
    HNS_PER_SECOND = 10000000 # 100-nanosecond intervals ต่อ 1 วินาที

    # --- 2. กำหนดวันที่เป้าหมาย (Local Time) ---
    # สร้างวัตถุ datetime จาก ค.ศ. ที่ป้อน
    local_time = datetime(year_ce, month, day, hour, minute, second)
    
    # --- 3. แปลงเวลาท้องถิ่นเป็น UTC ---
    # ต้องลบ Time Zone Offset ออกเพื่อให้ได้เวลา UTC ที่แท้จริง
    tz_offset = timedelta(hours=timezone_offset_hours)
    utc_time = local_time - tz_offset
    
    # --- 4. คำนวณค่า FILETIME ---
    # คำนวณระยะเวลา (timedelta) ตั้งแต่ 1601 UTC ถึงวันที่หมดอายุ UTC
    # .replace(tzinfo=timezone.utc) เพื่อให้ Python รู้ว่าเรากำลังทำงานกับ UTC Time
    time_difference = utc_time.replace(tzinfo=timezone.utc) - WINDOWS_EPOCH
    
    # แปลงเป็นช่วงเวลา 100-nanosecond intervals
    accountExpires_value = int(time_difference.total_seconds() * HNS_PER_SECOND)
    
    return accountExpires_value

def get_current_time_gmt7():
    """
    ฟังก์ชันนี้ใช้สำหรับดึงเวลาปัจจุบันในเขตเวลา GMT+7 (UTC+7)
    :return: datetime object ของเวลาปัจจุบันในเขตเวลา GMT+7
    """
    # ดึงเวลา UTC ปัจจุบัน
    utc_now = datetime.now(timezone.utc)
    
    # แปลงเป็นเวลา GMT+7 โดยการบวก 7 ชั่วโมง
    gmt7_offset = timedelta(hours=7)
    gmt7_now = utc_now + gmt7_offset
    
    # คืนค่าเป็น datetime โดยไม่รวม timezone information
    return gmt7_now.replace(tzinfo=None)

def update_active_directory():
    # สร้าง record สำหรับเก็บประวัติการ sync
    sync_record = SyncHistory(sync_type='ad', status='running')
    db.session.add(sync_record)
    db.session.commit()
    try:
        server = Server(Config.AD_SERVER, get_info=ALL)
        user = f"{Config.AD_USER}@{Config.AD_DOMAIN}"
        conn = Connection(server, user=user, password=Config.AD_PASSWORD, auto_bind=True)

        # ดึงรายการพนักงานที่ยังไม่ได้อัพเดตใน AD
        employees_to_update = Employee.query.filter_by(ad_updated=False).all()
        
        updated_count = 0
        not_found_count = 0
        log_messages = []

        for employee in employees_to_update:
            # ค้นหาผู้ใช้ใน AD โดยใช้ fname และ lname (เหมือนเดิม)
            search_filter = f"(&(objectClass=user)(givenName={employee.fname})(sn={employee.lname}))"
            conn.search(search_base=Config.AD_BASE_DN, search_filter=search_filter, attributes=['distinguishedName', 'userAccountControl'])
            
            if conn.entries:
                # ถ้าพบผู้ใช้ใน AD
                dn = conn.entries[0].distinguishedName.value
                uac = int(conn.entries[0].userAccountControl.value)
                
                changes = {}
                
                # อัพเดต employee ID ถ้ามี
                if employee.employee_id:
                    changes['employeeID'] = [(MODIFY_REPLACE, [employee.employee_id])]
                
                # อัพเดตข้อมูลทั่วไป
                if employee.email:
                    changes['mail'] = [(MODIFY_REPLACE, [employee.email])]
                if employee.phone:
                    changes['telephoneNumber'] = [(MODIFY_REPLACE, [employee.phone])]
                if employee.department:
                    changes['department'] = [(MODIFY_REPLACE, [employee.department])]
                if employee.position:
                    changes['title'] = [(MODIFY_REPLACE, [employee.position])]
                
                # จัดการการปิดใช้งานบัญชี
                if employee.status.lower() == 'inactive' or employee.resigndate:
                    # ตั้งค่า userAccountControl เพื่อปิดใช้งานบัญชี
                    if not (uac & 0x0002):
                        new_uac = uac | 0x0002
                        changes['userAccountControl'] = [(MODIFY_REPLACE, [str(new_uac)])]
                    
                    # กำหนดวันที่หมดอายุของบัญชี (ถ้ามี)
                    if employee.account_expires_date:
                        expires_date = employee.account_expires_date
                        # แปลง date เป็น datetime เพื่อให้ subtraction ทำงานได้
                        expires_datetime = datetime.combine(expires_date, datetime.min.time())
                        
                        # ใช้ฟังก์ชัน convert_ce_to_ad_filetime ในการแปลงค่า
                        # ส่งปี ค.ศ. และเวลา 23:59:59 พร้อม timezone offset +7
                        filetime_value = convert_ce_to_ad_filetime(
                            expires_datetime.year,
                            expires_datetime.month,
                            expires_datetime.day,
                            23, 59, 59, 7
                        )
                        
                        changes['accountExpires'] = [(MODIFY_REPLACE, [str(filetime_value)])]
                else:
                    # ถ้าพนักงานยังทำงานอยู่ ให้เปิดใช้งานบัญชี
                    if uac & 0x0002:
                        new_uac = uac & ~0x0002
                        changes['userAccountControl'] = [(MODIFY_REPLACE, [str(new_uac)])]
                    
                    # ตั้งค่า accountExpires เป็น 0 หมายถึงไม่มีวันหมดอายุ
                    changes['accountExpires'] = [(MODIFY_REPLACE, ["0"])]
                
                if changes:
                    conn.modify(dn, changes)
                    if employee.employee_id:
                        log_messages.append(f"Updated AD user: {employee.fname} {employee.lname} (ID: {employee.employee_id})")
                    else:
                        log_messages.append(f"Updated AD user: {employee.fname} {employee.lname}")
                    updated_count += 1
                else:
                    if employee.employee_id:
                        log_messages.append(f"No changes needed for AD user: {employee.fname} {employee.lname} (ID: {employee.employee_id})")
                    else:
                        log_messages.append(f"No changes needed for AD user: {employee.fname} {employee.lname}")
                
                # อัพเดตสถานะในฐานข้อมูลว่าอัพเดตใน AD เรียบร้อยแล้ว
                employee.ad_updated = True
                db.session.add(employee)
            else:
                # ถ้าไม่พบผู้ใช้ใน AD
                if employee.employee_id:
                    log_messages.append(f"User not found in AD with ID: {employee.employee_id} ({employee.fname} {employee.lname})")
                else:
                    log_messages.append(f"User not found in AD: {employee.fname} {employee.lname}")
                not_found_count += 1
        
        db.session.commit()
        conn.unbind()

        # อัปเดต record ว่าสำเร็จ
        sync_record.status = 'success'
        sync_record.end_time = get_asia_bangkok_time()
        sync_record.message = f"AD Sync completed. Updated: {updated_count}, Not found: {not_found_count}"
        sync_record.details = json.dumps(log_messages) # แปลง list เป็น JSON string
        sync_record.updated_count = updated_count
        sync_record.not_found_count = not_found_count
        db.session.add(sync_record)
        db.session.commit()
        
        # ส่งคืนผลลัพธ์พร้อมข้อความ log
        result = {
            'success': True,
            'updated_count': updated_count,
            'not_found_count': not_found_count,
            'log_messages': log_messages
        }
        return result
        
    except Exception as e:
        print(f"Error updating Active Directory: {e}")
        db.session.rollback()

        # อัปเดต record ว่าล้มเหลว
        sync_record.status = 'failed'
        sync_record.end_time = get_asia_bangkok_time()
        sync_record.error_message = str(e)
        db.session.add(sync_record)
        db.session.commit()
        
        return {
            'success': False,
            'error': str(e),
            'updated_count': 0,
            'not_found_count': 0,
            'log_messages': []
        }