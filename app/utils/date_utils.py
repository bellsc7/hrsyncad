from datetime import datetime, timezone, timedelta

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