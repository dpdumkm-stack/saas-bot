// Dynamic tier-based personalization
const urlParams = new URLSearchParams(window.location.search);
const selectedTier = urlParams.get('tier') || 'TRIAL';

// Update UI based on tier
const tierConfig = {
    'TRIAL': {
        title: '🚀 Coba GRATIS 5 Hari',
        subtitle: 'Tidak perlu kartu kredit. Bot aktif dalam 2 menit!',
        button: '✨ Aktifkan Bot Gratis Sekarang',
        footer: '✅ Gratis 5 Hari • ✅ Tidak Perlu Kartu Kredit • ✅ Bisa Dibatalkan Kapan Saja'
    },
    'STARTER': {
        title: '📦 Aktivasi Paket Starter',
        subtitle: 'Mulai otomasi bisnis Anda dengan AI (Rp 99k/bulan)',
        button: '💳 Lanjut ke Pembayaran',
        footer: '✅ 200 Chat/Bulan • ✅ AI 24/7 • ✅ Support Lengkap'
    },
    'BUSINESS': {
        title: '💼 Aktivasi Paket Business',
        subtitle: 'Tingkatkan penjualan dengan AI pintar (Rp 199k/bulan)',
        button: '💳 Lanjut ke Pembayaran',
        footer: '✅ Chat Unlimited • ✅ Cek Bukti Bayar • ✅ VIP Support'
    },
    'PRO': {
        title: '⭐ Aktivasi Paket Pro',
        subtitle: 'Solusi lengkap autopilot bisnis (Rp 349k/bulan)',
        button: '💳 Lanjut ke Pembayaran',
        footer: '✅ Semua Fitur • ✅ 5 Nomor WA • ✅ API Access'
    }
};

const config = tierConfig[selectedTier] || tierConfig['TRIAL'];
document.getElementById('pageTitle').textContent = config.title;
document.getElementById('pageSubtitle').textContent = config.subtitle;
document.getElementById('btnSubmit').textContent = config.button;
// document.getElementById('footerText').textContent = config.footer; // Element not found in original HTML, assumed safe to keep logic or ignore if errors not critical

// Form handling
const form = document.getElementById('registerForm');
const btnSubmit = document.getElementById('btnSubmit');
const alertBox = document.getElementById('alertBox');

function showAlert(message, type = 'error') {
    alertBox.className = `alert alert-${type}`;
    alertBox.textContent = message;
    alertBox.style.display = 'block';

    setTimeout(() => {
        alertBox.style.display = 'none';
    }, 5000);
}

form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const name = document.getElementById('storeName').value.trim();
    const phone = document.getElementById('storePhone').value.trim();
    const category = document.getElementById('storeCategory').value;
    const pairingMethod = document.querySelector('input[name="deviceCount"]:checked').value;

    if (!name || !phone || !category) {
        showAlert('Mohon lengkapi semua data!');
        return;
    }

    // Disable button
    btnSubmit.disabled = true;
    btnSubmit.textContent = '⏳ Memproses...';

    try {
        const response = await fetch('/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                phone: phone,
                name: name,
                category: category,
                tier: selectedTier,
                pairing_method: pairingMethod
            })
        });

        const result = await response.json();

        if (result.status === 'success' && result.redirect_url) {
            showAlert('✅ Berhasil! Mengarahkan ke aktivasi...', 'success');
            setTimeout(() => {
                window.location.href = result.redirect_url;
            }, 1000);
        } else {
            showAlert('❌ ' + (result.message || 'Pendaftaran gagal. Coba lagi.'));
            btnSubmit.disabled = false;
            btnSubmit.textContent = '✨ Aktifkan Bot Gratis Sekarang';
        }
    } catch (error) {
        console.error(error);
        showAlert('❌ Terjadi kesalahan koneksi. Coba lagi.');
        btnSubmit.disabled = false;
        btnSubmit.textContent = '✨ Aktifkan Bot Gratis Sekarang';
    }
});
