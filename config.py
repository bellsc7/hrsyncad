import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-very-secret-key-for-session'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://pacifica:P%40cific%402018@10.210.1.3/hr_sync_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # MyHR API Config
    MYHR_API_URL = 'https://api.myhr.com/employees' # แก้ไข URL ให้ถูกต้อง
    MYHR_API_KEY = 'your-api-key-here' # ใส่ API Key จริง
   
   # FTP Config
    FTP_HOST = 'localhost' # แก้ไข Host ให้ถูกต้อง
    FTP_USER = 'ftpuser'
    FTP_PASSWORD = '123456'
    FTP_PATH = '/'
    
    # Active Directory Config
    AD_SERVER = '10.210.1.5'
    AD_DOMAIN = 'itpacifica.local'
    AD_USER = 'administrator'
    AD_PASSWORD = 'P@cific@2018'
    AD_BASE_DN = 'DC=itpacifica,DC=local'