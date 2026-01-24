let countdown = 25;
let countdownInterval;

function updateCountdown() {
    countdown--;
    document.getElementById('countdown').textContent = countdown;

    const timerEl = document.getElementById('timer');
    if (countdown <= 5) {
        timerEl.classList.add('warning');
    } else {
        timerEl.classList.remove('warning');
    }

    if (countdown <= 0) {
        refreshQR();
    }
}

function refreshQR() {
    const img = document.getElementById('qrImage');
    img.classList.add('loading');

    // Add timestamp to prevent caching
    const timestamp = new Date().getTime();
    img.src = `/api/qr?t=${timestamp}`;

    // Reset countdown
    countdown = 25;
    clearInterval(countdownInterval);
    countdownInterval = setInterval(updateCountdown, 1000);

    // Show status
    showStatus('QR Code diperbarui!', 'success');

    setTimeout(() => {
        img.classList.remove('loading');
    }, 500);
}

function showStatus(message, type) {
    const statusEl = document.getElementById('status');
    statusEl.textContent = message;
    statusEl.className = `status ${type}`;

    setTimeout(() => {
        statusEl.textContent = '';
        statusEl.className = '';
    }, 3000);
}

// Check if session is already connected
function checkSessionStatus() {
    fetch('/api/waha_status')
        .then(res => res.json())
        .then(data => {
            if (data.status === 'WORKING') {
                showStatus('✅ WhatsApp sudah tersambung!', 'success');
                clearInterval(countdownInterval);
                document.querySelector('.qr-container').innerHTML =
                    '<div style="padding:40px;color:#25D366;font-size:48px;">✅</div><p style="color:#25D366;font-weight:bold;font-size:18px;">WhatsApp Tersambung!</p>';

                // Show Logout Button when connected
                const btn = document.getElementById('resetBtn');
                btn.style.display = 'inline-block';
                btn.textContent = '🚪 Logout / Scan Ulang';
                btn.onclick = resetSession; // Ensure function is bound
            }
        })
        .catch(err => console.error('Status check failed:', err));
}

// Reset Session Logic
function resetSession() {
    if (!confirm('Apakah Anda yakin ingin me-reset koneksi? Ini akan logout session saat ini dan membuat QR baru.')) return;

    const btn = document.getElementById('resetBtn');
    const originalText = btn.textContent;
    btn.textContent = '⏳ Mereset Sistem...';
    btn.disabled = true;
    btn.style.opacity = '0.7';

    fetch('/api/reset_session', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                showStatus('✅ Reset Berhasil! Memuat ulang...', 'success');
                setTimeout(() => location.reload(), 2000);
            } else {
                alert('Gagal reset: ' + data.error);
                btn.textContent = originalText;
                btn.disabled = false;
                btn.style.opacity = '1';
            }
        })
        .catch(err => {
            alert('Error network: ' + err);
            btn.textContent = originalText;
            btn.disabled = false;
            btn.style.opacity = '1';
        });
}

// Start countdown
countdownInterval = setInterval(updateCountdown, 1000);

// Check status every 10 seconds
setInterval(checkSessionStatus, 10000);
checkSessionStatus();

// Handle image load errors
document.getElementById('qrImage').onerror = function () {
    showStatus('❌ Gagal memuat QR Code. Mencoba lagi...', 'error');
    setTimeout(refreshQR, 3000);
};
