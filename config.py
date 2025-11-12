import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-very-secret-key-for-session'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://pacifica:P%40cific%402017@10.20.1.247/hr_sync_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # MyHR API Config
    MYHR_API_URL = 'https://api.myhr.com/employees' # แก้ไข URL ให้ถูกต้อง
    MYHR_API_KEY = 'your-api-key-here' # ใส่ API Key จริง
   
   # FTP Config
    FTP_HOST = '161.82.212.91' # แก้ไข Host ให้ถูกต้อง
    FTP_USER = 'ftpuser'
    FTP_PASSWORD = '123456'
    FTP_PATH = '/'
    
    # Active Directory Config
    AD_SERVER = '192.168.2.10'
    AD_PORT = 389  # Default LDAP port
    AD_USE_SSL = False  # Set to True if using LDAPS (port 636)
    AD_DOMAIN = 'pacifica.local'
    AD_USER = 'administrator'
    AD_PASSWORD = 'P@cific@2017'
    AD_BASE_DN = 'DC=pacifica,DC=local'
    AD_CONNECTION_TIMEOUT = 30  # Connection timeout in seconds
    AD_READ_TIMEOUT = 30  # Read timeout in seconds
    AD_MAX_RETRIES = 3  # Maximum connection retry attempts
    AD_RETRY_DELAY = 5  # Delay between retries in seconds