# Kebutuhan lengkap dan status rilis lokal

11 November 2026 (WIB). Tujuan sekarang: deliverable portofolio lokal yang dapat dijalankan tanpa key dan tanpa biaya tambahan. Bukan klaim produk AI live atau submission hackathon selesai. Branch `feature/offline-release-v1` meneruskan `feature/complete-local-mvp` tanpa mengubah main.

| ID | Kebutuhan kecil | Acceptance / bukti | Status |
| --- | --- | --- | --- |
| B01 | Inventaris baseline dan histori | Parser terdahulu dan laporan lama dipertahankan; branch remote dijadikan parent | PASS |
| B02 | Setup Python dan dependency | `scripts.doctor`, `pip check` | PASS |
| B03 | Startup satu perintah | `scripts.run_demo`; hanya proses milik launcher yang dihentikan | PASS |
| B04 | Input OpenAPI bounded | Subset validator + regression tests invalid/ref/depth/size | PASS |
| B05 | Rule/plan fixture transparan | Label fixture, rule terbatas dan dua kasus tervalidasi | PASS |
| B06 | Adapter Meta terpisah | Schema tertutup, error jelas, mock tests, tanpa fallback | PASS untuk kode/mock; live BLOCKED |
| B07 | Grounding plan | Endpoint/status/schema/pointer/rule reference tervalidasi | PASS |
| B08 | Review dan consent | Dua checkbox, plan immutable server, TTL/capacity | PASS |
| B09 | Target lokal saja | Allowlist exact loopback, strict payload, redirect/proxy ditolak | PASS |
| B10 | Request/response bounded | Case/time/byte/depth caps; streaming response UI diperbaiki | PASS |
| B11 | Evidence deterministik | Status/JSON subset type-aware, UTC timestamps, latency, reproduksi/redaction | PASS |
| B12 | State tidak basi | Rule/spec/mode/controller/target berubah membatalkan plan/consent/receipt | PASS |
| B13 | Hasil mudah dibaca | Expected/actual berdampingan, summary error/incomplete/matched | PASS otomatis; visual BLOCKED |
| B14 | Export JSON | Download receipt nyata melalui widget | PASS otomatis |
| B15 | Export HTML mandiri | Validasi receipt, escape untrusted text, tanpa script/network | PASS; contoh actual di evidence/*.html |
| B16 | Demo API buggy | Smoke aktual menghasilkan PASS/FAIL yang diharapkan | PASS |
| B17 | Demo API corrected | `--variant corrected`; smoke aktual menghasilkan PASS/PASS | PASS |
| B18 | Perbandingan baseline/control | 18 request, raw receipts direkonsiliasi ke metrics | PASS untuk fixture; live NOT RUN |
| B19 | Pemeriksaan rilis satu perintah | `python -m scripts.verify_release` menyimpan release_check.json | PASS |
| B20 | Dokumentasi kontrak konsisten | Framework diperbaiki dari cases bebas ke issued plan_id; port 8501 | PASS |
| B21 | Browser desktop/mobile dan keyboard | Playwright siap dipanggil; Chromium gagal startup karena socket tidak diizinkan | BLOCKED lingkungan; bukan PASS |
| B22 | Screenshot/video aktual | Tidak dibuat karena browser tidak berhasil dibuka | BLOCKED B21 |
| B23 | Pengujian manusia/reviewer independen | Perangkat nyata, readability/focus, catat durasi alur | NOT RUN |
| B24 | Aktivasi Meta tanpa biaya tak disetujui | Key+akses/kuota aktual; jangan beli langganan demi menyelesaikan demo | BLOCKED akun/billing |
| B25 | Pengujian Meta live | Actual model response dan reviewed execution, biaya terukur bila tersedia | BLOCKED B24 |
| B26 | Rules/eligibility/submission | Bukti akun/aturan final/portal, tanpa asumsi on-time | NOT VERIFIED; di luar rilis offline |
| B27 | Commit/push dan verifikasi remote | Tree dan branch remote sama dengan deliverable lokal | Diselesaikan pada akhir eksekusi; lihat laporan chat/commit GitHub |

## Crosscheck kedua: detail yang sempat terlewat

1. Fingerprint UI belum memasukkan target. Sudah diperbaiki dan dites agar consent tidak terbawa ke target berbeda.
2. UI mengecek ukuran setelah seluruh respons dibuffer. Sekarang dibatasi selama streaming; regression test memastikan stream dihentikan sebelum 20 chunk.
3. Framework masih mencantumkan port 8502 dan eksekusi cases bebas. Sudah diselaraskan dengan kontrak server-issued plan.
4. Corrected control sebelumnya hanya di evaluasi runner; sekarang tersedia melalui launcher dan full widget/HTTP smoke.
5. Bukti hanya JSON kurang nyaman dibaca di luar aplikasi. HTML mandiri kini menyajikan actual receipt, CSP dan escaping; tidak dianggap signed audit.
6. Klaim screenshot/video atau mobile QA tidak boleh disimpulkan dari AppTest. Percobaan browser gagal sebelum page dibuka dan dicatat BLOCKED.

## Batas hasil

Tidak ada kredensial baru, pembelian, perubahan billing, real funds, deployment publik, merge main atau submission. Tidak ada pengujian model Meta aktual. 162 tes dan smoke lokal adalah bukti engineering, bukan bukti AI, keamanan menyeluruh atau keunggulan bisnis. Dokumen A01–A10 tetap menjadi daftar gate live/event/manual; B21–B25 merinci hambatan rilis sekarang.
