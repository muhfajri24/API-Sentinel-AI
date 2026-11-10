# Menjalankan dan memulihkan demo lokal

## Jalur tanpa API key

Dari root repo, gunakan Python 3.11+ dan virtual environment:

```sh
python -m pip install -r requirements-dev.txt
python -m scripts.doctor
python -m scripts.run_demo
```

Buka http://127.0.0.1:8501. Tidak perlu metode pembayaran, login Muse, atau API key. Fixture memakai kasus tetap; aturan lain tidak diinterpretasikan. Review kedua request dan expected outcome, centang dua izin terpisah, Execute. Hasil PASS/FAIL pada buggy target adalah perilaku demo yang benar.

Untuk menunjukkan perbedaan setelah bug pada target diperbaiki, hentikan launcher pertama dengan Ctrl+C, lalu:

```sh
python -m scripts.run_demo --variant corrected
```

Generate/review ulang. Hasil semestinya PASS/PASS. Ini variant target sintetis yang dipilih operator, bukan perbaikan otomatis oleh AI.

## Pemeriksaan lengkap

```sh
python -m scripts.verify_release
```

Jangan jalankan bersamaan dengan launcher lain karena port yang sama digunakan. Perintah ini memeriksa setup, dependency, lint, semua tes, smoke kedua variant dan evaluasi, lalu membuat HTML dari receipt aktual. Exit nonzero berarti pemeriksaan tidak selesai/lulus; baca langkah terakhir dan release_check.json. Perintah tidak memanggil Meta. Default evaluasi hanya fixture dan baseline.

## Masalah umum

| Gejala | Tindakan |
| --- | --- |
| Port occupied | Hentikan terminal milikmu yang menggunakan 8100/8101/8501, lalu ulangi. Launcher tidak membunuh proses yang sudah ada. |
| Module not found | Aktifkan venv, jalankan instalasi requirements dari root repo. Gunakan `python -m scripts.run_demo`, bukan `python scripts/run_demo.py`. |
| Plan missing/expired | Generate dan review ulang. Cache hilang saat restart dan TTL 30 menit. |
| Tombol Execute disabled | Review seluruh expected outcome lalu centang dua checkbox. Perubahan input membatalkan persetujuan lama. |
| Fixture rule rejected | Kembalikan rule contoh README. Fixture tidak menerima rule sembarang sebagai hasil AI. |
| Meta billing/key tidak tersedia | Gunakan launcher fixture; tidak perlu beli langganan. Live gate tetap BLOCKED. |
| UI/controller mode mismatch | Launcher mengatur keduanya fixture. Untuk live, konfigurasi semua proses harus sama; jangan samarkan fallback. |
| ERROR / NOT_RUN | Baca receipt; request mungkin belum terkirim atau outcome tidak diketahui bila timeout inflight. Jangan mengartikannya sebagai PASS. |
| Browser capture gagal socket | Lingkungan ini tidak mengizinkan startup Chromium. Jalankan optional browser check pada perangkat lokal yang mendukungnya; jangan klaim screenshot sudah dibuat. |

## Export

Download JSON untuk data lengkap atau HTML untuk laporan mandiri yang dapat dibuka offline/print dari browser. File berisi payload sintetis, provenance, expected/actual dan latency. File dapat diedit dan bukan signed evidence. Contoh hasil actual: evidence/local_smoke.html dan evidence/corrected_smoke.html.

## Optional browser QA

Butuh Node.js, Playwright 1.62.1 dan Chromium. Di lingkungan developer yang sesuai, install Playwright terpisah (`npm install --no-save playwright@1.62.1`), set CHROMIUM_PATH ke executable Chromium jika bukan /usr/bin/chromium, lalu `python -m scripts.capture_demo`. Tool merekam alur fixture desktop, cek unduhan/stale-state, kemudian mobile 390px dan overflow. Tool ini gagal sebelum page dibuka di environment eksekusi saat ini; hasil visual/rekaman belum diverifikasi. Simpan rekaman hanya setelah memeriksa tidak ada informasi sensitif. Ini automated browser QA, tetap bukan pengujian manusia.
