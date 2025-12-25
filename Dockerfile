# Gunakan image Python resmi yang ringan sebagai dasar
FROM python:3.9-slim

# Set folder kerja di dalam kontainer ke /app
WORKDIR /app

# Install dependensi sistem yang diperlukan
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Salin file requirements.txt dari folder bot/ ke dalam kontainer
COPY bot/requirements.txt .

# Install semua library Python
RUN pip install --no-cache-dir -r requirements.txt

# Salin seluruh isi folder bot/ ke dalam kontainer
COPY bot/ .

# Jalankan aplikasi menggunakan Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:app"]
