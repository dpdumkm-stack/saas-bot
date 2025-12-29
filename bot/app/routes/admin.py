from flask import Blueprint, render_template, request, session, render_template_string
import time
from app.models import Toko

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/')
def landing_page():
    return render_template('landing.html')

@admin_bp.route('/tutorial')
def tutorial():
    return render_template('tutorial.html')

@admin_bp.route('/success')
def success_page():
    return render_template('success.html')



@admin_bp.route('/subscribe')
def subscribe_page():
    return render_template('subscribe.html')

@admin_bp.route('/admin/qr')
def qr_page():
    return render_template('qr_scan.html', timestamp=int(time.time()))

@admin_bp.route('/remote/<token>', methods=['GET', 'POST'])
def remote_view(token):
    toko = Toko.query.filter_by(remote_token=token).first()
    if not toko:
        return "403 Forbidden", 403
    
    if session.get(f'auth_{token}') != True:
        if request.method == 'POST':
            pin = request.form.get('pin', '')
            if pin == toko.remote_pin:
                session[f'auth_{token}'] = True
                session.permanent = True
                return render_template('remote.html', toko=toko, user_token=token)
            return "PIN Salah", 401
        return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head><title>Login</title></head>
            <body style="display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;">
                <form method=post style="padding:2rem;border:1px solid #ddd;border-radius:8px;">
                    <h2>Masukkan PIN</h2>
                    <input type=password name=pin placeholder="PIN" required style="padding:0.5rem;font-size:1rem;">
                    <button style="padding:0.5rem 1rem;margin-left:0.5rem;">Masuk</button>
                </form>
            </body>
            </html>
        """)

    return render_template('remote.html', toko=toko, user_token=token)
