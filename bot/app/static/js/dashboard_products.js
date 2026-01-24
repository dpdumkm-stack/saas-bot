// DOM Elements
const addModal = document.getElementById('addModal');
const editModal = document.getElementById('editModal');
const deleteModal = document.getElementById('deleteModal');
const searchInput = document.getElementById('searchInput');

// Add Product
function openAddModal() {
    addModal.classList.add('active');
}

function closeAddModal() {
    addModal.classList.remove('active');
    document.getElementById('addForm').reset();
}

async function submitAddProduct(e) {
    e.preventDefault();
    const btn = e.target.querySelector('.btn-save');
    const originalText = btn.innerText;
    btn.innerText = 'Menyimpan...';
    btn.disabled = true;

    const formData = new FormData(e.target);

    try {
        const res = await fetch('/dashboard/products/add', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (data.status === 'success') {
            location.reload();
        } else {
            alert('Gagal menambah produk: ' + data.message);
        }
    } catch (err) {
        alert('Terjadi kesalahan koneksi');
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
    }
}

// Edit Product
function openEditModal(id, item, price, stock, category, desc, img) {
    document.getElementById('editId').value = id;
    document.getElementById('editItem').value = item;
    document.getElementById('editHarga').value = price;
    document.getElementById('editStok').value = stock;
    document.getElementById('editCategory').value = category;
    document.getElementById('editDescription').value = desc || '';
    document.getElementById('editImageUrl').value = img || '';

    // Set form action dynamically if needed, or handle in JS
    editModal.classList.add('active');
}

function closeEditModal() {
    editModal.classList.remove('active');
}

async function submitEditProduct(e) {
    e.preventDefault();
    const id = document.getElementById('editId').value;
    const btn = e.target.querySelector('.btn-save');
    const originalText = btn.innerText;
    btn.innerText = 'Menyimpan...';
    btn.disabled = true;

    const formData = new FormData(e.target);

    try {
        const res = await fetch(`/dashboard/products/edit/${id}`, {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (data.status === 'success') {
            location.reload();
        } else {
            alert('Gagal update produk: ' + data.message);
        }
    } catch (err) {
        alert('Terjadi kesalahan koneksi');
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
    }
}

// Delete Product
let deleteId = null;

function confirmDelete(id) {
    deleteId = id;
    deleteModal.classList.add('active');
}

function closeDeleteModal() {
    deleteModal.classList.remove('active');
    deleteId = null;
}

async function executeDelete() {
    if (!deleteId) return;

    const btn = document.getElementById('btnConfirmDelete');
    btn.innerText = 'Menghapus...';
    btn.disabled = true;

    try {
        const res = await fetch(`/dashboard/products/delete/${deleteId}`, {
            method: 'POST'
        });
        const data = await res.json();

        if (data.status === 'success') {
            location.reload();
        } else {
            alert('Gagal menghapus: ' + data.message);
        }
    } catch (err) {
        alert('Terjadi kesalahan koneksi');
    }
}

// Search Filter
searchInput.addEventListener('keyup', function (e) {
    const term = e.target.value.toLowerCase();
    const rows = document.querySelectorAll('.product-table tbody tr');

    rows.forEach(row => {
        const text = row.innerText.toLowerCase();
        if (text.includes(term)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
});

// Helper for currency format
function formatRupiah(num) {
    return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR' }).format(num);
}
