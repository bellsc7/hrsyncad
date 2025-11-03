from app_factory import db, get_asia_bangkok_time
from datetime import datetime

class SyncHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sync_type = db.Column(db.String(20), nullable=False)  # 'myhr', 'ftp', 'ad', 'all'
    status = db.Column(db.String(20), nullable=False)   # 'success', 'failed'
    message = db.Column(db.Text)
    details = db.Column(db.Text)  # เก็บ log แบบ JSON string
    start_time = db.Column(db.DateTime, default=get_asia_bangkok_time)
    end_time = db.Column(db.DateTime)
    updated_count = db.Column(db.Integer, default=0)
    not_found_count = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)