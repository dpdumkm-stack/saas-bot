// ===== METHOD SWITCHING =====
function switchMethod(method) {
    const qrSection = document.getElementById('qrSection');
    const codeSection = document.getElementById('codeSection');
    const methodBadge = document.getElementById('methodBadge');

    if (method === 'qr') {
        qrSection.classList.add('active');
        codeSection.classList.remove('active');
        methodBadge.textContent = '📱 QR Code Method';
    } else {
        qrSection.classList.remove('active');
        codeSection.classList.add('active');
        methodBadge.textContent = '🔢 Pairing Code Method';
    }
}

// ===== URL PARAMETERS =====
const params = new URLSearchParams(window.location.search);
const orderId = window.WA_ORDER_ID || params.get('order_id');
const method = params.get('method') || 'qr';
const session = window.WA_SESSION_NAME || `session_${orderId}`;
const phoneNumber = window.WA_PHONE_NUMBER || "";
let isConnected = false;
let pairingCodeValue = null;

// Initialize - trust server rendering first, or URL params if needed
if (method === 'code') {
    document.getElementById('methodBadge').textContent = '📱 Metode: Pairing Code';
    document.getElementById('pageSubtitle').textContent = 'Masukkan kode 8 angka di WhatsApp Anda';
    // Logic: display checks handled by CSS .active class from server
    requestPairingCode();
} else {
    document.getElementById('methodBadge').textContent = '⚡ Metode: QR Scan';
    document.getElementById('pageSubtitle').textContent = 'Scan QR code dengan WhatsApp Anda';
    loadQR();
    setInterval(loadQR, 20000);
}

// Check connection status for both methods
setInterval(checkStatus, 3000);

let qrRetryCount = 0;
const MAX_QR_RETRIES = 5;

async function loadQR() {
    if (isConnected) return;

    const qrImg = document.getElementById('qrImage');
    const qrLoading = document.getElementById('qrLoading');
    const qrError = document.getElementById('qrError');
    const loadingText = document.querySelector('.qr-loading-text');

    // Show loading state
    if (qrLoading) qrLoading.style.display = 'block';
    if (qrError) qrError.style.display = 'none';
    qrImg.style.display = 'none';
    if (loadingText) loadingText.textContent = 'Memuat QR Code...';

    try {
        // Poll API using fetch first to check status
        const response = await fetch(`/api/qr?session=${session}&t=${Date.now()}`);

        if (response.ok && response.headers.get('content-type').includes('image')) {
            // Success: Now set image src for actual display
            qrRetryCount = 0;
            if (qrLoading) qrLoading.style.display = 'none';
            qrImg.src = `/api/qr?session=${session}&t=${Date.now()}`;
            qrImg.style.display = 'block';
            console.log('QR Code loaded successfully');
        } else if (response.status === 503) {
            // Retry case: Session is starting/restarting
            if (loadingText) loadingText.textContent = 'Menyiapkan session... (Mohon tunggu)';
            console.log('Session starting (503), retrying in 5s...');
            setTimeout(loadQR, 5000);
        } else {
            throw new Error(`API Error: ${response.status}`);
        }
    } catch (err) {
        console.error('QR Load Fail:', err);
        qrRetryCount++;

        if (qrRetryCount < MAX_QR_RETRIES) {
            console.log(`Retrying QR (${qrRetryCount}/${MAX_QR_RETRIES})...`);
            setTimeout(loadQR, 5000);
        } else {
            if (qrLoading) qrLoading.style.display = 'none';
            if (qrError) qrError.style.display = 'block';
            qrRetryCount = 0;
        }
    }
}

function retryLoadQR() {
    qrRetryCount = 0;
    loadQR();
}

// Retries for pairing code
let codeRetryCount = 0;
const MAX_CODE_RETRIES = 3;

async function requestPairingCode() {
    const codeDisplay = document.getElementById('pairingCode');
    const copyBtn = document.getElementById('copyCodeBtn');
    const errorDiv = document.getElementById('codeError');
    const statusBadge = document.getElementById('statusBadge');

    // Reset UI
    if (errorDiv) errorDiv.style.display = 'none';
    copyBtn.style.display = 'inline-block';

    // Loading state in the code display
    codeDisplay.textContent = '...';
    codeDisplay.style.color = '#94a3b8';

    try {
        const res = await fetch('/api/pairing/request-code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_name: session })
        });

        const data = await res.json();

        if (data.status === 'success' && data.code) {
            // SUCCESS
            pairingCodeValue = data.code;
            codeDisplay.textContent = data.code; // Format: ####-####
            codeDisplay.style.color = '#1e293b';

            document.getElementById('codeHint').textContent = data.code;

            statusBadge.className = 'status-badge status-ready';
            statusBadge.innerHTML = '<span class="spin">⏳</span><span>Menunggu Anda memasukkan kode...</span>';

            // Reset retries on success
            codeRetryCount = 0;

        } else {
            // API Error (e.g. Session Starting)
            throw new Error(data.message || 'Gagal mendapatkan kode');
        }
    } catch (err) {
        console.error("Pairing Code Error:", err);

        // Auto-retry if it's likely a startup issue
        codeRetryCount++;
        if (codeRetryCount <= MAX_CODE_RETRIES) {
            console.log(`Retrying Code Request (${codeRetryCount}/${MAX_CODE_RETRIES})...`);
            codeDisplay.textContent = `Retrying (${codeRetryCount})...`;
            setTimeout(requestPairingCode, 3000);
        } else {
            // Hard Fail -> Show Retry Button
            codeDisplay.textContent = 'ERROR';
            codeDisplay.style.color = '#ef4444';
            copyBtn.style.display = 'none';
            if (errorDiv) errorDiv.style.display = 'block';
            statusBadge.innerHTML = `<span>❌ Gagal memuat kode. Pastikan sesi aktif.</span>`;
        }
    }
}

function retryPairingCode() {
    codeRetryCount = 0;
    requestPairingCode();
}

async function checkStatus() {
    if (isConnected) return;

    try {
        const res = await fetch('/api/pairing/check-status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_name: session })
        });

        const data = await res.json();
        if (data.status === 'success' && data.session_status === 'WORKING') {
            handleSuccess();
        }
    } catch (err) {
        // Silent fail
    }
}

function handleSuccess() {
    if (isConnected) return;
    isConnected = true;

    document.getElementById('activationArea').style.display = 'none';
    document.getElementById('successArea').style.display = 'block';

    if (typeof confetti !== 'undefined') {
        confetti({
            particleCount: 100,
            spread: 70,
            origin: { y: 0.6 }
        });
    }
}

function copyCode() {
    if (!pairingCodeValue) return;

    navigator.clipboard.writeText(pairingCodeValue).then(() => {
        const btn = document.getElementById('copyCodeBtn');
        const original = btn.textContent;
        btn.textContent = '✅ TERSALIN!';
        btn.style.background = '#059669';

        setTimeout(() => {
            btn.textContent = original;
            btn.style.background = '#10b981';
        }, 2000);
    });
}
