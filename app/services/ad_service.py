import json
import socket
import time
import logging
from app.models.sync_history import SyncHistory
from ldap3 import Server, Connection, ALL, MODIFY_REPLACE
from ldap3.core.exceptions import LDAPException
from app_factory import db, get_asia_bangkok_time
from app.models.employee import Employee
from app.utils.network_diagnostics import troubleshoot_ad_connection
from config import Config
from datetime import datetime, timezone, timedelta

# Configure logging for AD service
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def test_ad_server_connectivity(server_host, port=389, timeout=10):
    """
    Test basic TCP connectivity to AD server
    """
    try:
        logger.info(f"Testing connectivity to AD server {server_host}:{port}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((server_host, port))
        sock.close()
        
        if result == 0:
            logger.info(f"Successfully connected to {server_host}:{port}")
            return True
        else:
            logger.error(f"Failed to connect to {server_host}:{port} - Error code: {result}")
            return False
    except socket.error as e:
        logger.error(f"Socket error when testing connectivity to {server_host}:{port}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error when testing connectivity to {server_host}:{port}: {e}")
        return False

def create_ad_connection_with_retry():
    """
    Create AD connection with retry mechanism and proper timeout settings
    """
    server_host = Config.AD_SERVER
    server_port = getattr(Config, 'AD_PORT', 389)  # Default LDAP port
    max_retries = getattr(Config, 'AD_MAX_RETRIES', 3)
    retry_delay = getattr(Config, 'AD_RETRY_DELAY', 5)
    connection_timeout = getattr(Config, 'AD_CONNECTION_TIMEOUT', 30)
    read_timeout = getattr(Config, 'AD_READ_TIMEOUT', 30)
    use_ssl = getattr(Config, 'AD_USE_SSL', False)
    
    # Test basic connectivity first
    if not test_ad_server_connectivity(server_host, server_port):
        raise Exception(f"Cannot establish basic TCP connection to AD server {server_host}:{server_port}")
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting AD connection (attempt {attempt + 1}/{max_retries})")
            
            # Create server with timeout settings
            server = Server(
                server_host,
                port=server_port,
                get_info=ALL,
                connect_timeout=connection_timeout,
                use_ssl=use_ssl
            )
            
            user = f"{Config.AD_USER}@{Config.AD_DOMAIN}"
            
            # Create connection with explicit timeout
            conn = Connection(
                server,
                user=user,
                password=Config.AD_PASSWORD,
                auto_bind=True,
                client_strategy='SYNC',
                receive_timeout=read_timeout,
                raise_exceptions=True
            )
            
            logger.info(f"Successfully connected to AD server {server_host}")
            return conn
            
        except LDAPException as e:
            logger.error(f"LDAP error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                raise Exception(f"Failed to connect to AD after {max_retries} attempts: {e}")
        except socket.timeout as e:
            logger.error(f"Socket timeout on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                raise Exception(f"Connection timeout to AD server after {max_retries} attempts: {e}")
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                raise Exception(f"Failed to connect to AD after {max_retries} attempts: {e}")

def update_active_directory():
    # สร้าง record สำหรับเก็บประวัติการ sync
    sync_record = SyncHistory(sync_type='ad', status='running')
    db.session.add(sync_record)
    db.session.commit()
    
    conn = None
    try:
        logger.info("Starting AD synchronization process")
        
        # Use the new connection method with retry
        conn = create_ad_connection_with_retry()

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
                if employee.phone:
                    changes['telephoneNumber'] = [(MODIFY_REPLACE, [employee.phone])]
                if employee.department:
                    changes['department'] = [(MODIFY_REPLACE, [employee.department])]
                if employee.position:
                    changes['title'] = [(MODIFY_REPLACE, [employee.position])]
                
                # จัดการการปิดใช้งานบัญชี - ตรวจสอบเฉพาะเมื่อมีวันที่ลาออกจริง
                if employee.resigndate:
                    # ตรวจสอบว่าวันที่ลาออกผ่านไปแล้วหรือยัง
                    current_date = get_current_time_gmt7().date()
                    
                    if employee.resigndate <= current_date:
                        # ถ้าวันที่ลาออกผ่านไปแล้ว ให้ปิดใช้งานบัญชี
                        if not (uac & 0x0002):
                            new_uac = uac | 0x0002
                            changes['userAccountControl'] = [(MODIFY_REPLACE, [str(new_uac)])]
                        
                        # กำหนดวันที่หมดอายุของบัญชีตามวันที่ลาออก
                        expires_date = employee.resigndate
                        # แปลง date เป็น datetime เพื่อให้ subtraction ทำงานได้
                        expires_datetime = datetime.combine(expires_date, datetime.min.time())
                        
                        # ใช้ฟังก์ชัน convert_ce_to_ad_filetime ในการแปลงค่า
                        # ส่งปี ค.ศ. และเวลา 23:59:59 พร้อม timezone offset +7
                        # แต่เพื่อให้ตรงกับวันที่ลาออกพอดี เราต้องเพิ่ม 1 วัน
                        next_day = expires_date + timedelta(days=1)
                        filetime_value = convert_ce_to_ad_filetime(
                            next_day.year,
                            next_day.month,
                            next_day.day,
                            0, 0, 0, 7
                        )
                        
                        changes['accountExpires'] = [(MODIFY_REPLACE, [str(filetime_value)])]
                    else:
                        # ถ้าวันที่ลาออกยังไม่ถึง ให้เปิดใช้งานบัญชีแต่ตั้งวันหมดอายุ
                        if uac & 0x0002:
                            new_uac = uac & ~0x0002
                            changes['userAccountControl'] = [(MODIFY_REPLACE, [str(new_uac)])]
                        
                        # กำหนดวันที่หมดอายุของบัญชีตามวันที่ลาออก
                        expires_date = employee.resigndate
                        # แปลง date เป็น datetime เพื่อให้ subtraction ทำงานได้
                        expires_datetime = datetime.combine(expires_date, datetime.min.time())
                        
                        # ใช้ฟังก์ชัน convert_ce_to_ad_filetime ในการแปลงค่า
                        # ส่งปี ค.ศ. และเวลา 23:59:59 พร้อม timezone offset +7
                        # แต่เพื่อให้ตรงกับวันที่ลาออกพอดี เราต้องเพิ่ม 1 วัน
                        next_day = expires_date + timedelta(days=1)
                        filetime_value = convert_ce_to_ad_filetime(
                            next_day.year,
                            next_day.month,
                            next_day.day,
                            0, 0, 0, 7
                        )
                        
                        changes['accountExpires'] = [(MODIFY_REPLACE, [str(filetime_value)])]
                else:
                    # ถ้าพนักงานยังทำงานอยู่ (ไม่มีวันที่ลาออก) ให้เปิดใช้งานบัญชี
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
        
    except LDAPException as e:
        logger.error(f"LDAP error during AD synchronization: {e}")
        db.session.rollback()

        # อัปเดต record ว่าล้มเหลว
        sync_record.status = 'failed'
        sync_record.end_time = get_asia_bangkok_time()
        sync_record.error_message = f"LDAP Error: {str(e)}"
        db.session.add(sync_record)
        db.session.commit()
        
        return {
            'success': False,
            'error': f"LDAP Error: {str(e)}",
            'updated_count': 0,
            'not_found_count': 0,
            'log_messages': [f"LDAP Error: {str(e)}"]
        }
        
    except socket.timeout as e:
        logger.error(f"Socket timeout during AD synchronization: {e}")
        db.session.rollback()

        # Run network diagnostics when timeout occurs
        diagnostics = troubleshoot_ad_connection()
        logger.info(f"Network diagnostics completed: {diagnostics['diagnostics']['overall_status']}")
        
        # อัปเดต record ว่าล้มเหลว
        sync_record.status = 'failed'
        sync_record.end_time = get_asia_bangkok_time()
        sync_record.error_message = f"Connection Timeout: {str(e)}"
        sync_record.details = json.dumps({
            'error': f"Connection Timeout: {str(e)}",
            'diagnostics': diagnostics['diagnostics'],
            'recommendations': diagnostics['recommendations']
        })
        db.session.add(sync_record)
        db.session.commit()
        
        return {
            'success': False,
            'error': f"Connection Timeout: {str(e)}",
            'updated_count': 0,
            'not_found_count': 0,
            'log_messages': [f"Connection Timeout: {str(e)}"] + diagnostics['recommendations']
        }
        
    except socket.error as e:
        logger.error(f"Socket error during AD synchronization: {e}")
        db.session.rollback()

        # Run network diagnostics when socket error occurs
        diagnostics = troubleshoot_ad_connection()
        logger.info(f"Network diagnostics completed: {diagnostics['diagnostics']['overall_status']}")
        
        # อัปเดต record ว่าล้มเหลว
        sync_record.status = 'failed'
        sync_record.end_time = get_asia_bangkok_time()
        sync_record.error_message = f"Network Error: {str(e)}"
        sync_record.details = json.dumps({
            'error': f"Network Error: {str(e)}",
            'diagnostics': diagnostics['diagnostics'],
            'recommendations': diagnostics['recommendations']
        })
        db.session.add(sync_record)
        db.session.commit()
        
        return {
            'success': False,
            'error': f"Network Error: {str(e)}",
            'updated_count': 0,
            'not_found_count': 0,
            'log_messages': [f"Network Error: {str(e)}"] + diagnostics['recommendations']
        }
        
    except Exception as e:
        logger.error(f"Unexpected error during AD synchronization: {e}")
        db.session.rollback()

        # อัปเดต record ว่าล้มเหลว
        sync_record.status = 'failed'
        sync_record.end_time = get_asia_bangkok_time()
        sync_record.error_message = f"Unexpected Error: {str(e)}"
        db.session.add(sync_record)
        db.session.commit()
        
        return {
            'success': False,
            'error': f"Unexpected Error: {str(e)}",
            'updated_count': 0,
            'not_found_count': 0,
            'log_messages': [f"Unexpected Error: {str(e)}"]
        }
        
    finally:
        # Ensure connection is properly closed
        if conn:
            try:
                conn.unbind()
                logger.info("AD connection closed successfully")
            except Exception as e:
                logger.warning(f"Error closing AD connection: {e}")