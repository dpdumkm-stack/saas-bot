"""
Superadmin Routes
Dashboard for superadmin to manage broadcasts, view analytics, and manage platform
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from app.models import BroadcastJob, Subscription, Customer, Toko
from app.extensions import db
from app.config import Config
from datetime import datetime, timedelta
import functools
import os
import logging
import traceback

superadmin_bp = Blueprint('superadmin', __name__, url_prefix='/superadmin')

# Superadmin password (stored in env for security)
SUPERADMIN_PASSWORD = os.getenv('SUPERADMIN_PASSWORD', 'admin123')  # Change in production!

def superadmin_required(f):
    """Decorator to require superadmin authentication"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_superadmin'):
            # If AJAX/API request, return JSON instead of redirecting
            if request.is_json or \
               request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
               request.path.startswith('/superadmin/api/') or \
               request.path == '/superadmin/broadcast/send':
                return jsonify({'status': 'error', 'message': 'Sesi habis, silakan login kembali'}), 401
            return redirect(url_for('superadmin.login'))
        return f(*args, **kwargs)
    return decorated_function

@superadmin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Superadmin login page"""
    if request.method == 'POST':
        password = request.form.get('password')
        
        if password == SUPERADMIN_PASSWORD:
            session['is_superadmin'] = True
            session.permanent = True
            return redirect(url_for('superadmin.dashboard'))
        else:
            return render_template('superadmin/login.html', error="Password salah")
    
    return render_template('superadmin/login.html')

@superadmin_bp.route('/logout')
def logout():
    """Logout superadmin"""
    session.pop('is_superadmin', None)
    return redirect(url_for('superadmin.login'))

@superadmin_bp.route('/')
@superadmin_required
def dashboard():
    """Main dashboard with platform stats"""
    # Stats
    total_merchants = Subscription.query.count()
    active_merchants = Subscription.query.filter_by(status='ACTIVE').count()
    total_broadcasts = BroadcastJob.query.count()
    
    # New Stats for the requested Card (Phase 10A+)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    sent_today = db.session.query(db.func.sum(BroadcastJob.success_count)).filter(
        BroadcastJob.created_at >= today_start
    ).scalar() or 0
    
    active_jobs_count = BroadcastJob.query.filter(
        BroadcastJob.status.in_(['PENDING', 'RUNNING'])
    ).count()
    
    # Recent broadcasts
    recent_broadcasts = BroadcastJob.query.order_by(BroadcastJob.created_at.desc()).limit(5).all()
    
    return render_template('superadmin/dashboard.html',
                         total_merchants=total_merchants,
                         active_merchants=active_merchants,
                         total_broadcasts=total_broadcasts,
                         sent_today=sent_today,
                         active_jobs_count=active_jobs_count,
                         recent_broadcasts=recent_broadcasts)

@superadmin_bp.route('/broadcast')
@superadmin_required
def broadcast():
    """Broadcast campaign page"""
    from app.services.broadcast_manager import BroadcastManager
    
    # Get available segments with counts
    segments = BroadcastManager.get_available_segments()

    # Calculate today's stats for the premium card
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    sent_today = db.session.query(db.func.sum(BroadcastJob.success_count)).filter(
        BroadcastJob.created_at >= today_start
    ).scalar() or 0
    
    active_jobs_count = BroadcastJob.query.filter(
        BroadcastJob.status.in_(['PENDING', 'RUNNING'])
    ).count()
    
    # Dynamic Timezone Helper (Internal)
    def get_tz_offset():
        # Fallback to 7 (WIB) if anything fails
        try:
            from app.models import Toko
            # For superadmin dashboard, we might want a global setting or context
            # Currently we'll use WIB as default for superadmin, but this logic
            # is ready to be expanded per-store.
            return 7
        except: return 7

    tz_offset = get_tz_offset()
    
    # Fetch templates for the quick-select feature
    from app.models import BroadcastTemplate
    templates = BroadcastTemplate.query.order_by(BroadcastTemplate.name.asc()).all()
    
    return render_template('superadmin/broadcast.html', 
                         segments=segments,
                         sent_today=sent_today,
                         active_jobs_count=active_jobs_count,
                         templates=templates,
                         tz_offset=tz_offset)

@superadmin_bp.route('/broadcast/send', methods=['POST'])
@superadmin_required
def send_broadcast():
    """Send broadcast via dashboard"""
    try:
        from app.services.broadcast_manager import BroadcastManager
        from app.services.csv_handler import parse_csv_content, CSVValidationError
        from app.feature_flags import FeatureFlags
        
        # Check if feature enabled
        if not FeatureFlags.is_broadcast_enabled():
            return jsonify({'status': 'error', 'message': 'Fitur broadcast sedang maintenance'}), 503
        
        execution_type = request.form.get('execution_type', 'now')
        message = request.form.get('message')
        target_type = request.form.get('target_type')  # 'segment' or 'csv'
        
        if not message:
            return jsonify({'status': 'error', 'message': 'Pesan tidak boleh kosong'}), 400
            
        # Determine targets (CSV or Segment)
        targets = []
        source = 'manual'
        
        if target_type == 'segment':
            segment = request.form.get('segment')
            targets = BroadcastManager.get_segment_targets(segment)
            source = segment
            if not targets:
                return jsonify({'status': 'error', 'message': f'Segment {segment} kosong'}), 400
        elif target_type == 'csv':
            if 'csv_file' not in request.files:
                return jsonify({'status': 'error', 'message': 'File CSV belum diupload'}), 400
            file = request.files['csv_file']
            if file.filename == '':
                return jsonify({'status': 'error', 'message': 'Tidak ada file terpilih'}), 400
            try:
                from app.services.csv_handler import robust_decode
                content = robust_decode(file.read())
                targets = parse_csv_content(content)
                source = 'csv_upload'
            except CSVValidationError as e:
                return jsonify({'status': 'error', 'message': f'Validasi CSV: {str(e)}'}), 400
            except Exception as e:
                return jsonify({'status': 'error', 'message': f'Error baca CSV: {str(e)}'}), 400
        elif target_type == 'paste':
            content = request.form.get('paste_content')
            if not content:
                return jsonify({'status': 'error', 'message': 'Data tempel (paste) kosong'}), 400
            try:
                # Use strict=False logic or ensure parse_csv_content handles raw newlines well.
                # Actually parse_csv_content splits by newline and handles no-header nicely.
                targets = parse_csv_content(content)
                source = 'manual_paste'
            except CSVValidationError as e:
                return jsonify({'status': 'error', 'message': f'Validasi Paste: {str(e)}'}), 400
            except Exception as e:
                return jsonify({'status': 'error', 'message': f'Error proses data: {str(e)}'}), 400
        
        import json
        # FIX: Save FULL target object (phone + name) for scheduling to support personalization
        target_list_json = json.dumps(targets)

        # 1. Handle Scheduled Broadcast
        if execution_type == 'schedule':
            from app.models import ScheduledBroadcast
            sched_time_str = request.form.get('scheduled_at')
            recurrence = request.form.get('recurrence', 'once')
            job_name = request.form.get('job_name') or f"Schedule {(datetime.utcnow() + timedelta(hours=7)).strftime('%d/%m %H:%M')}"
            
            if not sched_time_str:
                return jsonify({'status': 'error', 'message': 'Waktu penjadwalan harus diisi'}), 400
            
            try:
                # Dynamic Timezone Logic
                from app.models import Toko
                # For now assume superadmin uses WIB, but code is ready for store-specific tz
                tz_offset = 7 
                
                # FIX: Handle Timezone. Input is assumed to be Local from UI
                # Cloud Run uses UTC, so we must convert input (Local) -> UTC
                scheduled_local = datetime.fromisoformat(sched_time_str)
                scheduled_utc = scheduled_local - timedelta(hours=tz_offset) 
                
                if scheduled_utc < datetime.utcnow():
                    return jsonify({'status': 'error', 'message': 'Waktu penjadwalan tidak boleh di masa lalu'}), 400
                
                new_schedule = ScheduledBroadcast(
                    name=job_name,
                    scheduled_at=scheduled_utc,
                    recurrence=recurrence,
                    message=message,
                    target_type=target_type,
                    target_segment=source if target_type == 'segment' else None,
                    target_list=target_list_json,
                    status='pending'
                )
                db.session.add(new_schedule)
                db.session.commit()
                
                tz_label = "WIB" if tz_offset == 7 else "WITA" if tz_offset == 8 else "WIT" if tz_offset == 9 else f"UTC+{tz_offset}"
                
                return jsonify({
                    'status': 'success', 
                    'message': f'Berhasil dijadwalkan untuk {scheduled_local.strftime("%Y-%m-%d %H:%M")} {tz_label}'
                })
            except Exception as e:
                db.session.rollback()
                return jsonify({'status': 'error', 'message': f'Gagal menjadwalkan: {str(e)}'}), 500

        # 2. Handle Immediate Broadcast (Original Flow)
        job_id = BroadcastManager.create_broadcast_job('SUPERADMIN', message, targets, source)
        
        if job_id:
            return jsonify({
                'status': 'success',
                'job_id': job_id,
                'target_count': len(targets),
                'message': f'Berhasil antre! Job #{job_id} dengan {len(targets)} nomor.'
            })
        else:
            return jsonify({'status': 'error', 'message': 'Gagal membuat antrean broadcast'}), 500

    except Exception as e:
        import traceback
        logging.error(f"FATAL BROADCAST ROUTE ERROR: {e}\n{traceback.format_exc()}")
        return jsonify({'status': 'error', 'message': f'Internal Server Error: {str(e)}'}), 500

@superadmin_bp.route('/broadcast/history')
@superadmin_required
def broadcast_history():
    """View broadcast history and analytics"""
    # Get all broadcast jobs
    jobs = BroadcastJob.query.order_by(BroadcastJob.created_at.desc()).limit(50).all()
    
    # Process jobs data
    jobs_data = []
    for job in jobs:
        import json
        target_list = json.loads(job.target_list) if job.target_list else []
        
        jobs_data.append({
            'id': job.id,
            'created_at': job.created_at,
            'status': job.status,
            'total_targets': len(target_list),
            'processed': job.processed_count,
            'message_preview': job.pesan[:50] + '...' if len(job.pesan) > 50 else job.pesan,
            'success_rate': (job.processed_count / len(target_list) * 100) if target_list else 0
        })
    
    return render_template('superadmin/history.html', jobs=jobs_data)

@superadmin_bp.route('/merchants')
@superadmin_required
def merchants():
    """View all merchants"""
    merchants = Subscription.query.order_by(Subscription.created_at.desc()).all()
    return render_template('superadmin/merchants.html', merchants=merchants)

@superadmin_bp.route('/api/toggle-panic', methods=['POST'])
@superadmin_required
def api_toggle_panic():
    """Toggle global panic mode"""
    from app.models import SystemConfig, AuditLog
    
    config = SystemConfig.query.get('panic_mode')
    if not config:
        config = SystemConfig(key='panic_mode', value='false')
        db.session.add(config)
    
    old_val = config.value
    new_val = 'true' if old_val.lower() == 'false' else 'false'
    config.value = new_val
    
    # Audit Log
    log = AuditLog(
        toko_id='SYSTEM',
        admin_hp='SUPERADMIN',
        action='TOGGLE_PANIC_MODE',
        target_type='SYSTEM_CONFIG',
        target_id='panic_mode',
        old_value=old_val,
        new_value=new_val
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'status': 'success', 'panic_mode': new_val == 'true'})

    return jsonify(jobs_data)

@superadmin_bp.route('/api/analytics/broadcasts')
@superadmin_required
def api_broadcast_analytics():
    """Get aggregated broadcast stats for Chart.js"""
    from app.models import BroadcastJob
    from sqlalchemy import func
    
    # Get total stats across all jobs
    stats = db.session.query(
        func.sum(BroadcastJob.success_count).label('success'),
        func.sum(BroadcastJob.failed_count).label('failed'),
        func.sum(BroadcastJob.skipped_count).label('skipped')
    ).first()
    
    # Get last 7 days of activity for trend chart
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    daily_stats = db.session.query(
        func.date(BroadcastJob.created_at).label('date'),
        func.sum(BroadcastJob.success_count).label('success'),
        func.sum(BroadcastJob.failed_count).label('failed')
    ).filter(BroadcastJob.created_at >= seven_days_ago).group_by('date').all()
    
    return jsonify({
        'totals': {
            'success': int(stats.success or 0),
            'failed': int(stats.failed or 0),
            'skipped': int(stats.skipped or 0)
        },
        'trends': [
            {'date': str(s.date), 'success': int(s.success or 0), 'failed': int(s.failed or 0)}
            for s in daily_stats
        ]
    })

@superadmin_bp.route('/api/active-schedules')
@superadmin_required
def api_active_schedules():
    """Get pending scheduled broadcasts"""
    from app.models import ScheduledBroadcast
    import json
    
    schedules = ScheduledBroadcast.query.filter_by(status='pending').order_by(ScheduledBroadcast.scheduled_at.asc()).all()
    
    data = []
    for s in schedules:
        target_count = 0
        if s.target_list:
            try:
                # Handle both string list and object list
                raw = json.loads(s.target_list)
                target_count = len(raw)
            except:
                target_count = 0
                
        # Dynamic Offset for current store context
        tz_offset = 7 # Default to WIB for superadmin list
        tz_label = "WIB" if tz_offset == 7 else "WITA" if tz_offset == 8 else "WIT" if tz_offset == 9 else "Local"
                
        data.append({
            'id': s.id,
            'name': s.name,
            # FIX: Convert UTC to Local for display
            'scheduled_at': (s.scheduled_at + timedelta(hours=tz_offset)).strftime('%d %b %Y %H:%M'),
            'tz_label': tz_label,
            'recurrence': s.recurrence,
            'message_preview': s.message[:50] + '...' if len(s.message) > 50 else s.message,
            'target_count': target_count,
            'target_type': s.target_type
        })
        
    return jsonify(data)

@superadmin_bp.route('/api/schedule/<int:sched_id>', methods=['DELETE'])
@superadmin_required
def api_delete_schedule(sched_id):
    """Cancel/Delete a scheduled broadcast"""
    from app.models import ScheduledBroadcast
    
    schedule = ScheduledBroadcast.query.get_or_404(sched_id)
    db.session.delete(schedule)
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': 'Jadwal berhasil dihapus'})

@superadmin_bp.route('/api/active-jobs')
@superadmin_required
def api_active_jobs():
    """Get active broadcast jobs for dashboard polling"""
    import json
    from app.services.broadcast import get_panic_mode
    
    # Include PENDING, RUNNING, and COMPLETED jobs that finished recently (within last 5 mins)
    five_mins_ago = datetime.utcnow() - timedelta(minutes=5)
    
    # 1. Get active jobs
    active_jobs = BroadcastJob.query.filter(
        BroadcastJob.status.in_(['PENDING', 'RUNNING', 'PAUSED'])
    ).order_by(BroadcastJob.created_at.desc()).all()
    
    # 2. ALWAYS get recently completed jobs (Show start/finish transition clearly)
    # Fetch last 3 completed jobs from the last hour
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    completed_jobs = BroadcastJob.query.filter(
        BroadcastJob.status == 'COMPLETED',
        BroadcastJob.updated_at >= one_hour_ago
    ).order_by(BroadcastJob.updated_at.desc()).limit(3).all()
    
    jobs = active_jobs + completed_jobs
    
    # Calculate real-time counts for the stats card
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    sent_today = db.session.query(db.func.sum(BroadcastJob.success_count)).filter(
        BroadcastJob.created_at >= today_start
    ).scalar() or 0
    active_jobs_count = BroadcastJob.query.filter(
        BroadcastJob.status.in_(['PENDING', 'RUNNING', 'PAUSED'])
    ).count()

    jobs_data = []
    for job in jobs:
        target_list = json.loads(job.target_list) if job.target_list else []
        jobs_data.append({
            'id': job.id,
            'status': job.status,
            'total': len(target_list),
            'processed': job.processed_count,
            'success': job.success_count,
            'failed': job.failed_count,
            'skipped': job.skipped_count,
            'target_list': target_list, # Enhanced for Live Monitoring
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'locked_until': job.locked_until.isoformat() if job.locked_until else None
        })
    
    return jsonify({
        'jobs': jobs_data,
        'panic_mode': get_panic_mode(),
        'sent_today': int(sent_today),
        'active_jobs_count': int(active_jobs_count)
    })

@superadmin_bp.route('/api/broadcast/<int:job_id>/status', methods=['POST'])
@superadmin_required
def api_update_broadcast_status(job_id):
    """Update broadcast job status (Pause/Resume/Cancel)"""
    from app.models import BroadcastJob
    
    data = request.json
    action = data.get('action') # 'pause', 'resume', 'stop'
    
    job = BroadcastJob.query.get_or_404(job_id)
    
    if action == 'stop':
        job.status = 'CANCELLED'
    elif action == 'pause':
        # Allow pausing even if currently "locked" (it will stop after current iteration)
        if job.status in ['PENDING', 'RUNNING']:
            job.status = 'PAUSED'
        else:
            return jsonify({'status': 'error', 'message': 'Hanya job berjalan yang bisa dipause'}), 400
    elif action == 'resume':
        if job.status == 'PAUSED':
            job.status = 'RUNNING' # Worker will pick it up
        else:
            return jsonify({'status': 'error', 'message': 'Hanya job dipause yang bisa diresume'}), 400
    elif action == 'retry':
        # Reset counters but keep status and processed_count=0 so worker skips successes
        job.status = 'PENDING'
        job.processed_count = 0
        job.success_count = 0
        job.failed_count = 0
        job.skipped_count = 0
        job.locked_until = None
    else:
        return jsonify({'status': 'error', 'message': 'Aksi tidak valid'}), 400
    
    db.session.commit()
    return jsonify({'status': 'success', 'new_status': job.status})

@superadmin_bp.route('/broadcast/<int:job_id>/download_failed')
@superadmin_required
def download_failed_csv(job_id):
    """Download failed targets for a specific job as CSV"""
    from app.models import BroadcastJob
    import json
    import csv
    from io import StringIO
    from flask import make_response
    
    job = BroadcastJob.query.get_or_404(job_id)
    targets = json.loads(job.target_list) if job.target_list else []
    
    # Filter failed
    failed_targets = [t for t in targets if t.get('status') == 'failed']
    
    if not failed_targets:
        return "No failed targets found", 404
        
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['phone', 'name', 'error_reason'])
    
    for t in failed_targets:
        phone = t.get('phone', t.get('phone_number', ''))
        name = t.get('name', t.get('nama', ''))
        error = t.get('error', 'Unknown Error')
        cw.writerow([phone, name, error])
        
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=failed_job_{job.id}.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@superadmin_bp.route('/templates')
@superadmin_required
def template_manager():
    """Template management page"""
    return render_template('superadmin/templates.html')

@superadmin_bp.route('/blacklist')
@superadmin_required
def blacklist_manager():
    """Blacklist management page"""
    return render_template('superadmin/blacklist.html')

# --- TEMPLATE APIS ---
@superadmin_bp.route('/api/templates', methods=['GET', 'POST'])
@superadmin_required
def api_templates():
    from app.models import BroadcastTemplate
    if request.method == 'POST':
        data = request.json
        tpl = BroadcastTemplate(
            name=data['name'],
            category=data.get('category', 'other'),
            message=data['message']
        )
        db.session.add(tpl)
        db.session.commit()
        return jsonify({'status': 'success'})
    
    templates = BroadcastTemplate.query.order_by(BroadcastTemplate.created_at.desc()).all()
    return jsonify([{
        'id': t.id, 'name': t.name, 'category': t.category, 
        'message': t.message, 'use_count': t.use_count, 
        'last_used': t.last_used.isoformat() if t.last_used else None
    } for t in templates])

@superadmin_bp.route('/api/templates/<int:id>', methods=['DELETE'])
@superadmin_required
def api_delete_template(id):
    from app.models import BroadcastTemplate
    tpl = BroadcastTemplate.query.get_or_404(id)
    db.session.delete(tpl)
    db.session.commit()
    return jsonify({'status': 'success'})

# --- BLACKLIST APIS ---
@superadmin_bp.route('/api/blacklist', methods=['GET'])
@superadmin_required
def api_blacklist():
    from app.models import BroadcastBlacklist
    q = request.args.get('q', '')
    query = BroadcastBlacklist.query
    if q:
        query = query.filter(BroadcastBlacklist.phone_number.contains(q))
    
    blacklist = query.order_by(BroadcastBlacklist.opted_out_at.desc()).all()
    return jsonify([{
        'phone_number': b.phone_number,
        'opted_out_at': b.opted_out_at.isoformat(),
        'reason': b.reason
    } for b in blacklist])

@superadmin_bp.route('/api/blacklist/<phone>', methods=['DELETE'])
@superadmin_required
def api_unblock_phone(phone):
    from app.models import BroadcastBlacklist
    b = BroadcastBlacklist.query.get_or_404(phone)
    db.session.delete(b)
    db.session.commit()
    return jsonify({'status': 'success'})
