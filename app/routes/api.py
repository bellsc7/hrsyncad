from flask import Blueprint, jsonify
from flask_login import login_required
from app.services import myhr_service, ftp_service, ad_service

bp = Blueprint('api', __name__)

@bp.route('/sync/myhr', methods=['POST'])
@login_required
def sync_myhr():
    success = myhr_service.fetch_employees_from_api()
    return jsonify({'success': success, 'message': 'MyHR API sync completed.'})

@bp.route('/sync/ftp', methods=['POST'])
@login_required
def sync_ftp():
    success = ftp_service.fetch_employees_from_ftp()
    return jsonify({'success': success, 'message': 'FTP sync completed.'})

@bp.route('/sync/ad', methods=['POST'])
@login_required
def sync_ad():
    result = ad_service.update_active_directory()
    return jsonify(result)

@bp.route('/sync/all', methods=['POST'])
@login_required
def sync_all():
    myhr_success = myhr_service.fetch_employees_from_api()
    ftp_success = ftp_service.fetch_employees_from_ftp()
    ad_success = ad_service.update_active_directory()
    
    return jsonify({
        'myhr_success': myhr_success,
        'ftp_success': ftp_success,
        'ad_success': ad_success,
        'message': 'Full sync process completed.'
    })