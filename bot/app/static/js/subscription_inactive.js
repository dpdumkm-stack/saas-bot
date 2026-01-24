async function reactivateNow() {
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
            window.location.href = '/dashboard/';
        } else {
            alert('❌ Error: ' + result.message);
        }
    } catch (error) {
        console.error(error);
        alert('❌ Terjadi kesalahan koneksi');
    }
}
