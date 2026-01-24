const params = new URLSearchParams(window.location.search);
const orderId = params.get('order_id');
let isConnected = false;
document.getElementById('shareLink').value = window.location.href;

if (!orderId) {
    alert('Order ID tidak ditemukan.');
} else {
    loadQR();
    setInterval(loadQR, 20000);
    setInterval(checkStatus, 5000);
}

async function loadQR() {
    if (isConnected) return;
    const qrImg = document.getElementById('qrImage');
    const qrLoading = document.getElementById('qrLoading');
    const badge = document.getElementById('statusBadge');
    const scanner = document.getElementById('scannerLine');

    qrImg.src = '/api/qr?session=' + orderId + '&t=' + Date.now();

    qrImg.onload = function () {
        qrImg.style.display = 'block';
        qrLoading.style.display = 'none';
        scanner.style.display = 'block';
        badge.className = 'status-badge badge-ready';
        badge.innerHTML = '<i class="bi bi-qr-code-scan"></i> <span>Siap Di-Scan</span>';
    };

    qrImg.onerror = function () {
        badge.innerHTML = '<i class="bi bi-arrow-repeat spin"></i> <span>Membangunkan Bot...</span>';
    };
}

async function checkStatus() {
    if (isConnected) return;
    try {
        const res = await fetch('/api/status?session=' + orderId);
        const data = await res.json();
        if (data.connected || data.status === 'WORKING') {
            handleSuccess();
        }
    } catch (err) { }
}

async function forceNewQR() {
    const badge = document.getElementById('statusBadge');
    badge.innerHTML = '<i class="bi bi-arrow-repeat spin"></i> <span>Me-Reset Sesi...</span>';
    try {
        await fetch('/api/reset_session', { method: 'POST' });
        setTimeout(loadQR, 2000);
    } catch (err) {
        location.reload();
    }
}

function handleSuccess() {
    if (isConnected) return;
    isConnected = true;

    // UI Toggle
    document.getElementById('activationArea').style.display = 'none';
    document.getElementById('successArea').style.display = 'block';

    // Progress Steps
    document.getElementById('progStep2').className = 'step completed';
    document.getElementById('progStep3').className = 'step active';

    // Celebration
    confetti({
        particleCount: 150,
        spread: 70,
        origin: { y: 0.6 },
        colors: ['#22c55e', '#3b82f6', '#f59e0b']
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showHelp(id) {
    document.querySelectorAll('.detail-box').forEach(b => b.classList.remove('active-box'));
    document.getElementById(id).classList.add('active-box');
    document.getElementById(id).scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function copyLink(e) {
    const copyText = document.getElementById("shareLink");
    copyText.select();
    copyText.setSelectionRange(0, 99999);
    document.execCommand("copy");

    const btn = e.currentTarget;
    const originalText = btn.innerHTML;
    btn.innerHTML = 'TERSALIN!';
    btn.style.background = '#4ade80';
    setTimeout(() => {
        btn.innerHTML = originalText;
        btn.style.background = 'var(--primary)';
    }, 2000);
}
