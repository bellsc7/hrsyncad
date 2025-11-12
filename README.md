# HR Active Directory Sync System

ระบบซิงโครไนซ์ข้อมูลพนักงานจาก MyHR API และ FTP ไปยัง Active Directory (AD) สำหรับองค์กร Pacifica

## ภาพรวมของระบบ

ระบบนี้พัฒนาด้วย Flask Framework ทำหน้าที่:
- ดึงข้อมูลพนักงานจาก MyHR API
- อ่านข้อมูลพนักงานจากไฟล์ CSV ผ่าน FTP
- อัปเดตข้อมูลพนักงานใน Active Directory
- จัดการวันที่ลาออกและการปิดใช้งานบัญชีผู้ใช้ใน AD
- แสดง Dashboard สำหรับติดตามสถานะการซิงโครไนซ์

## โครงสร้างของโปรเจค

```
adsyncsystem/
├── app/
│   ├── models/           # โมเดลฐานข้อมูล
│   │   ├── employee.py   # โมเดลข้อมูลพนักงาน
│   │   ├── sync_history.py # โมเดลประวัติการซิงโครไนซ์
│   │   └── user.py       # โมเดลผู้ใช้ระบบ
│   ├── routes/           # เส้นทาง API และหน้าเว็บ
│   │   ├── api.py        # API endpoints
│   │   ├── auth.py       # การยืนยันตัวตน
│   │   └── main.py       # หน้าหลัก
│   ├── services/         # บริการต่างๆ
│   │   ├── ad_service.py # บริการเชื่อมต่อ AD
│   │   ├── ftp_service.py # บริการอ่านข้อมูลจาก FTP
│   │   └── myhr_service.py # บริการเชื่อมต่อ MyHR API
│   ├── static/           # ไฟล์ CSS, JS
│   ├── templates/        # ไฟล์ HTML templates
│   └── utils/            # เครื่องมือช่วยเหลือ
├── app_factory.py        # สร้างแอปพลิเคชัน Flask
├── config.py             # การตั้งค่าระบบ
├── docker-compose.yml    # การตั้งค่า Docker Compose
├── Dockerfile            # การตั้งค่า Docker
├── requirements.txt      # แพ็คเกจ Python ที่ต้องการ
├── run.py                # ไฟล์รันแอปพลิเคชัน
└── wsgi.py               # WSGI entry point
```

## การติดตั้งและ Deploy

### 1. การติดตั้งด้วย Docker (แนะนำ)

#### ข้อกำหนดเบื้องต้น
- Docker และ Docker Compose
- PostgreSQL Database
- เครือข่ายที่สามารถเชื่อมต่อกับ Active Directory และ FTP Server ได้

#### ขั้นตอนการติดตั้ง

1. Clone โปรเจค:
```bash
git clone <repository-url>
cd adsyncsystem
```

2. สร้างไฟล์ `.env` สำหรับเก็บค่าตัวแปรสภาพแวดล้อม:
```bash
cp .env.example .env
```

3. แก้ไขไฟล์ `.env` ตามค่าที่ถูกต้อง:
```env
SECRET_KEY=your-very-secret-key-for-session
DATABASE_URL=postgresql://username:password@host/database
MYHR_API_URL=https://api.myhr.com/employees
MYHR_API_KEY=your-api-key-here
FTP_HOST=10.210.1.4
FTP_USER=ftpuser
FTP_PASSWORD=123456
FTP_PATH=/
AD_SERVER=10.210.1.5
AD_DOMAIN=itpacifica.local
AD_USER=administrator
AD_PASSWORD=P@cific@2018
AD_BASE_DN=DC=itpacifica,DC=local
```

4. สร้างและรัน container:
```bash
docker-compose up -d
```

5. ตรวจสอบสถานะ:
```bash
docker-compose ps
```

### 2. การติดตั้งแบบ Manual

#### ข้อกำหนดเบื้องต้น
- Python 3.12+
- PostgreSQL Database
- การเชื่อมต่อกับ Active Directory และ FTP Server

#### ขั้นตอนการติดต้น

1. ติดตั้ง Python dependencies:
```bash
pip install -r requirements.txt
```

2. ตั้งค่าฐานข้อมูล PostgreSQL:
```sql
CREATE DATABASE hr_sync_db;
CREATE USER pacifica WITH PASSWORD 'P@cific@2018';
GRANT ALL PRIVILEGES ON DATABASE hr_sync_db TO pacifica;
```

3. แก้ไขไฟล์ [`config.py`](config.py:1) ตามค่าที่ถูกต้องสำหรับสภาพแวดล้อมของคุณ

4. รันแอปพลิเคชัน:
```bash
python wsgi.py
```

## การใช้งานระบบ

### การเข้าสู่ระบบ

1. เปิดเบราว์เซอร์และไปที่ `http://localhost:5000`
2. เข้าสู่ระบบด้วย:
   - ชื่อผู้ใช้: `admin`
   - รหัสผ่าน: `admin123`

### ฟังก์ชันหลักของระบบ

#### 1. Dashboard
- แสดงรายการพนักงานทั้งหมด
- แสดงประวัติการซิงโครไนซ์ล่าสุด
- ปุ่มสำหรับดำเนินการซิงโครไนซ์

#### 2. การซิงโครไนซ์ข้อมูล

ระบบมี 3 วิธีในการซิงโครไนซ์ข้อมูล:

- **MyHR API Sync**: ดึงข้อมูลพนักงานจาก MyHR API
- **FTP Sync**: อ่านข้อมูลจากไฟล์ CSV บน FTP Server
- **AD Sync**: อัปเดตข้อมูลพนักงานใน Active Directory
- **Full Sync**: ดำเนินการทั้ง 3 ขั้นตอนตามลำดับ

#### 3. API Endpoints

- `POST /api/sync/myhr` - ซิงโครไนซ์ข้อมูลจาก MyHR API
- `POST /api/sync/ftp` - ซิงโครไนซ์ข้อมูลจาก FTP
- `POST /api/sync/ad` - อัปเดตข้อมูลใน Active Directory
- `POST /api/sync/all` - ดำเนินการซิงโครไนซ์ทั้งหมด
- `GET /api/employees` - ดึงข้อมูลพนักงานทั้งหมด

## การทำงานของระบบ

### 1. การดึงข้อมูลจาก MyHR API

ระบบจะเชื่อมต่อกับ MyHR API เพื่อดึงข้อมูลพนักงาน:
- ข้อมูลส่วนตัว (ชื่อ, นามสกุล, เบอร์โทรศัพท์)
- ข้อมูลการทำงาน (แผนก, ตำแหน่ง)
- วันที่เริ่มงานและวันที่ลาออก

### 2. การอ่านข้อมูลจาก FTP

ระบบจะเชื่อมต่อกับ FTP Server เพื่อ:
- ค้นหาไฟล์ CSV ในโฟลเดอร์ที่กำหนด
- อ่านข้อมูลพนักงานจากไฟล์ CSV
- อัปเดตข้อมูลในฐานข้อมูล
- ย้ายไฟล์ที่ประมวลผลแล้วไปยังโฟลเดอร์ `processed`

### 3. การอัปเดต Active Directory

ระบบจะอัปเดตข้อมูลพนักงานใน Active Directory:
- ค้นหาผู้ใช้จากชื่อและนามสกุล
- อัปเดตข้อมูลต่างๆ (Employee ID, โทรศัพท์, แผนก, ตำแหน่ง)
- จัดการสถานะบัญชีผู้ใช้:
  - ถ้ามีวันที่ลาออกและผ่านไปแล้ว → ปิดใช้งานบัญชี
  - ถ้ามีวันที่ลาออกแต่ยังไม่ถึง → เปิดใช้งานแต่ตั้งวันหมดอายุ
  - ถ้าไม่มีวันที่ลาออก → เปิดใช้งานบัญชี

### 4. การจัดการวันที่

ระบบรองรับการแปลงวันที่ระหว่าง:
- ปี พ.ศ. และ ค.ศ. (สำหรับข้อมูลจากไทย)
- ค่า FILETIME ของ Active Directory (สำหรับวันหมดอายุบัญชี)
- เขตเวลา Asia/Bangkok (UTC+7)

## การแก้ไขปัญหา

### ปัญหาการเชื่อมต่อฐานข้อมูล
- ตรวจสอบว่า PostgreSQL ทำงานอยู่
- ตรวจสอบค่า `DATABASE_URL` ในไฟล์ config
- ตรวจสอบสิทธิ์การเข้าถึงฐานข้อมูล

### ปัญหาการเชื่อมต่อ Active Directory
- ตรวจสอบว่า AD Server สามารถเข้าถึงได้
- ตรวจสอบข้อมูลการเข้าสู่ระบบ AD
- ตรวจสอบสิทธิ์ในการแก้ไขข้อมูลใน AD

### ปัญหาการเชื่อมต่อ FTP
- ตรวจสอบว่า FTP Server สามารถเข้าถึงได้
- ตรวจสอบข้อมูลการเข้าสู่ระบบ FTP
- ตรวจสอบสิทธิ์ในการอ่าน/เขียนไฟล์

### ปัญหาการซิงโครไนซ์
- ตรวจสอบประวัติการซิงโครไนซ์ในหน้า Dashboard
- ตรวจสอบ log ของ container: `docker-compose logs app`
- ตรวจสอบว่าข้อมูลพนักงานมีครบถ้วน

## การบำรุงรักษา

### การสำรองข้อมูล
- สำรองฐานข้อมูล PostgreSQL เป็นประจำ
- ตรวจสอบไฟล์ CSV บน FTP Server หลังการประมวลผล

### การอัปเดตระบบ
- อัปเดต dependencies: `pip install -r requirements.txt --upgrade`
- สร้าง image ใหม่: `docker-compose build`
- รันใหม่: `docker-compose up -d`

## ข้อมูลติดต่อ

หากมีข้อสงสัยหรือปัญหาในการใช้งาน กรุณาติดต่อ:
- ทีม IT Pacifica
- อีเมล: it.support@pacifica.com