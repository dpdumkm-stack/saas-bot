const modal = document.getElementById('settingsModal');

function openSettings() {
    modal.classList.remove('hidden');
}

function closeSettings() {
    modal.classList.add('hidden');
}

function toggleVisibility(id) {
    const input = document.getElementById(id);
    input.type = input.type === 'password' ? 'text' : 'password';
}

function showStatus(msg, type = 'success') {
    const el = document.getElementById('settingsStatus');
    el.innerText = msg;
    el.className = `block text-sm px-4 py-2 rounded-lg mb-4 ${type === 'success' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`;
    setTimeout(() => { el.classList.add('hidden'); }, 5000);
    el.classList.remove('hidden');
}

async function testConnection() {
    const apiKey = document.getElementById('geminiApiKey').value;
    const btn = document.getElementById('btnTest');

    if (!apiKey) { showStatus('Masukkan API Key dulu Kak.', 'error'); return; }

    btn.disabled = true;
    btn.innerText = 'Testing...';

    try {
        const res = await fetch('/dashboard/test_api', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ apiKey })
        });
        const data = await res.json();
        if (data.status === 'success') {
            showStatus('✅ Koneksi Berhasil! API Key Aktif.');
        } else {
            showStatus('❌ ' + (data.error || 'Gagal tersambung.'), 'error');
        }
    } catch (e) {
        showStatus('❌ Error koneksi ke server.', 'error');
    } finally {
        btn.disabled = false;
        btn.innerText = 'Test Koneksi';
    }
}

async function saveSettings() {
    const apiKey = document.getElementById('geminiApiKey').value;
    const btn = document.getElementById('btnSave');

    btn.disabled = true;
    btn.innerText = 'Menyimpan...';

    try {
        const res = await fetch('/dashboard/save_settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ apiKey })
        });
        const data = await res.json();
        if (data.status === 'success') {
            showStatus('✅ Pengaturan Disimpan!');
            setTimeout(closeSettings, 1500);
        } else {
            showStatus('❌ Gagal simpan: ' + data.error, 'error');
        }
    } catch (e) {
        showStatus('❌ Error jaringan.', 'error');
    } finally {
        btn.disabled = false;
        btn.innerText = 'Simpan';
    }
}

// Cancel Subscription Functions
function openCancelModal() {
    document.getElementById('cancelModal').classList.remove('hidden');
}

function closeCancelModal() {
    document.getElementById('cancelModal').classList.add('hidden');
    document.getElementById('cancelForm').reset();
    document.getElementById('confirmCancel').checked = false;
}

// Enable/disable cancel button based on checkbox
document.getElementById('confirmCancel')?.addEventListener('change', function () {
    const btn = document.getElementById('btnConfirmCancel');
    btn.disabled = !this.checked;
});

// Handle cancel form submission
document.getElementById('cancelForm')?.addEventListener('submit', async function (e) {
    e.preventDefault();

    const confirmCheckbox = document.getElementById('confirmCancel');
    if (!confirmCheckbox.checked) {
        alert('Mohon centang konfirmasi untuk melanjutkan');
        return;
    }

    const reason = document.getElementById('cancelReason').value || 'No reason provided';
    const feedback = document.getElementById('cancelFeedback').value;
    const fullReason = feedback ? `${reason}: ${feedback}` : reason;

    const btnSubmit = document.getElementById('btnConfirmCancel');
    btnSubmit.disabled = true;
    btnSubmit.textContent = 'Memproses...';

    try {
        const response = await fetch('/api/subscription/cancel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                phone_number: window.TOKO_ID,
                reason: fullReason,
                confirm: true
            })
        });

        const result = await response.json();

        if (result.status === 'success') {
            alert('✅ Langganan berhasil dibatalkan. Data Anda akan disimpan selama 30 hari.');
            location.reload();
        } else {
            alert('❌ Error: ' + result.message);
            btnSubmit.disabled = false;
            btnSubmit.textContent = 'Ya, Batalkan';
        }
    } catch (error) {
        console.error(error);
        alert('❌ Terjadi kesalahan koneksi');
        btnSubmit.disabled = false;
        btnSubmit.textContent = 'Ya, Batalkan';
    }
});

// Reactivate Subscription
async function reactivateSubscription() {
    if (!confirm('Yakin ingin reaktivasi langganan? Masa aktif akan diperpanjang.')) {
        return;
    }

    try {
        const response = await fetch('/api/subscription/reactivate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                phone_number: window.TOKO_ID
            })
        });

        const result = await response.json();

        if (result.status === 'success') {
            alert('🎉 Selamat datang kembali! Langganan berhasil direaktivasi.');
            location.reload();
        } else {
            alert('❌ Error: ' + result.message);
        }
    } catch (error) {
        console.error(error);
        alert('❌ Terjadi kesalahan koneksi');
    }
}

function confirmDelete() {
    if (confirm('⚠️ PERINGATAN! Anda akan menghapus semua riwayat chat dan memori AI. Tindakan ini tidak bisa dibatalkan.\n\nLanjutkan?')) {
        fetch('/dashboard/delete_data', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    alert('Data berhasil dibersihkan.');
                    location.reload();
                }
            });
    }
}

// Load Chart Data
fetch('/dashboard/api/stats')
    .then(response => response.json())
    .then(data => {
        const ctx = document.getElementById('chatChart').getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Jumlah Chat',
                    data: data.data,
                    borderColor: '#25D366',
                    tension: 0.4,
                    fill: true,
                    backgroundColor: 'rgba(37, 211, 102, 0.1)'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: { beginAtZero: true, ticks: { stepSize: 1 } }
                }
            }
        });
    });

// Check Bot Status and Show Warning Banner if Offline
fetch('/api/status')
    .then(response => response.json())
    .then(data => {
        const statusIndicator = document.getElementById('statusIndicator');
        const warningBanner = document.getElementById('botWarningBanner');

        if (data.status === 'WORKING' && data.connected) {
            // Bot connected - hide warning
            if (warningBanner) warningBanner.style.display = 'none';

            // Update status indicator
            statusIndicator.innerHTML = `
                <span class="w-3 h-3 rounded-full bg-green-500"></span>
                <span class="font-bold text-green-600">Online</span>
            `;
        } else {
            // Bot offline - show warning
            if (warningBanner) warningBanner.style.display = 'block';

            // Update status indicator
            statusIndicator.innerHTML = `
                <span class="w-3 h-3 rounded-full bg-red-500"></span>
                <span class="font-bold text-red-600">Offline</span>
            `;
        }
    })
    .catch(error => {
        console.error('Error checking bot status:', error);
        // Show warning on error
        const warningBanner = document.getElementById('botWarningBanner');
        if (warningBanner) warningBanner.style.display = 'block';
    });
