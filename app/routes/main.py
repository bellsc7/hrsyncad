from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from app_factory import db
from app.models.employee import Employee
from app.models.sync_history import SyncHistory

bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/dashboard')
@login_required
def dashboard():
    # ดึงข้อมูลพนักงานทั้งหมดจากฐานข้อมูล
    all_employees = Employee.query.order_by(Employee.lname).all()
    
    # ดึงประวัติการ Sync 10 รายการล่าสุด
    recent_syncs = SyncHistory.query.order_by(SyncHistory.start_time.desc()).limit(4).all()
    
    # ส่งข้อมูลไปยัง template
    return render_template('dashboard.html', employees=all_employees, sync_history=recent_syncs)

@bp.route('/sync/<int:sync_id>/details')
@login_required
def sync_details(sync_id):
    sync_record = SyncHistory.query.get_or_404(sync_id)
    details = []
    if sync_record.details:
        try:
            import json
            details = json.loads(sync_record.details)
        except json.JSONDecodeError:
            details = [sync_record.details] # ถ้าไม่ใช่ JSON ให้ใส่ใน list
    
    return render_template('sync_details.html', sync=sync_record, details=details)

@bp.route('/employees')
@login_required
def employees():
    all_employees = Employee.query.all()
    employees_data = [
        {
            'employee_id': emp.employee_id,
            'fname': emp.fname,
            'lname': emp.lname,
            'phone': emp.phone,
            'department': emp.department,
            'position': emp.position,
            'start_date': emp.start_date.strftime('%Y-%m-%d') if emp.start_date else None,
            'status': emp.status,
            'ad_updated': emp.ad_updated
        } for emp in all_employees
    ]
    return jsonify(employees_data)