async function updateStok(token, index, change) {
    const res = await fetch('/api/update_counter', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hp: token, index: index, change: change })
    });
    const data = await res.json();
    if (data.status === 'success') location.reload();
}
