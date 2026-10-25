# API SENTINEL AI — META HACKATHON MASTER PROMPT v2.0

> **Sumber revisi:** `hackathon-master-prompt (3) (1)(1).md` milik Muhammad Fajri. Prinsip yang dipertahankan: problem nyata, inovasi, side-by-side demo, anti-generic UX, bukti teknis, dan evaluasi kritis. Disesuaikan menjadi *project-specific operating system*, bukan template ideasi umum. Pembaruan: 25 Oktober 2026 (WIB).

## 0. CARA MEMAKAI

- **ChatGPT = strategic brain / lead architect / reviewer.** Gunakan dokumen ini sebagai konteks keputusan dan peninjauan hasil Codex.
- **Codex = coding executor.** Baca `AGENTS.md` (instruksi repository), `docs/PROJECT_FRAMEWORK.md`, `docs/RULES_COMPLIANCE.md`, lalu kerjakan **satu task kecil** di `docs/CODEX_TASKS.md` per iterasi.
- **Muhammad Fajri = project owner.** Mengizinkan perubahan scope, akun/API berbayar, deployment publik, dan penyerahan submission.
- Jangan paste seluruh master prompt setiap kali menjalankan task Codex; Codex cukup membaca `AGENTS.md` dan file docs terkait.
- Project name locked: **API Sentinel AI**. Track: **Indie Developer**. Theme: **Push the Frontier**.

## 1. IDENTITAS DAN KENDALA

- Developer: Muhammad Fajri; bidang Full Stack / ML Engineering; preferensi Python.
- Kompetisi: Meta Global AI Developer Hackathon 2026; virtual; target pengerjaan **10 hari**.
- Target: **working MVP pada hari ke-7**, hari 8–10 untuk benchmark, perbaikan, video dan submission.
- Kapasitas: solo developer; low-cost; local-first; tidak melatih model sendiri, tidak mengandalkan GPU besar.
- Produk: AI membantu developer mengubah **OpenAPI + aturan bisnis bahasa natural** menjadi **test scenario terstruktur**, menjalankan tes pada **lingkungan yang diizinkan**, membandingkan hasil aktual dengan expected behavior, lalu mengeluarkan evidence.
- AI runtime: **Meta Muse Spark** melalui **Meta Model API**, `muse-spark-1.3` sebagai default yang saat ini didokumentasikan, dengan konfigurasi `MODEL_API_KEY`, base URL `https://api.meta.ai/v1`. Bila nama/ketersediaan berubah, ikuti dokumentasi terkini, bukan hardcode asumsi usang.
- Codex adalah alat pembangun kode, **bukan pengganti pemakaian model Meta dalam produk**.

## 2. BUKTI ATURAN VS ASUMSI

### Terkonfirmasi dari halaman resmi (cek lagi sebelum submit)

1. Ada **Indie Developer Track** untuk individu/pelajar; deskripsi penilaian: *creativity, technical ambition, whether it works*.
2. Dua tema: **Build for Your World** dan **Push the Frontier**; tema Push the Frontier secara eksplisit mencakup tantangan software.
3. Jadwal yang ditampilkan: mulai **26 Oktober 2026**, submission **4 November 2026 pukul 21.00 ET**, dengan perubahan jadwal mungkin terjadi.
4. Model Meta yang disorot termasuk Muse Spark series dan akses melalui Model API; Muse Code adalah opsi coding agent.
5. Aplikasi pendaftaran dievaluasi berdasarkan project idea dan technical skill secara berbobot sama; ini adalah **kriteria pendaftaran**, **jangan salah tulis sebagai rubrik final penjurian proyek**.

### BELUM terkonfirmasi—wajib verifikasi aturan final

- Eligibility kode/pre-existing components dan ketentuan kapan kode kompetisi boleh dimulai.
- Kewajiban membuat repository publik, video demo, URL live, format dan kanal submission.
- Ketentuan tim, IP/lisensi, penggunaan data, AI-generated code, API credits dan usage limitations.
- Rubrik penjurian final yang lebih rinci, larangan/kebijakan khusus.

**Gate R0 — Rules Lock:** Setelah aturan final tersedia dan kamu diterima, simpan bukti/link/ringkasan ke `docs/RULES_COMPLIANCE.md`, tandai requirement satu per satu, dan revisi rencana yang bertentangan. Jangan mengklaim '100% compliant' jika R0 belum PASS.

Referensi resmi:
- https://dev.meta.ai/events/global-hackathon
- https://dev.meta.ai/docs/overview
- https://dev.meta.ai/docs/quickstart
- https://dev.meta.ai/docs/cookbook/structured-output

## 3. PROBLEM — JOB TO BE DONE

> “Bagaimana developer bisa membuktikan API mengikuti aturan bisnis, bukan cuma mengembalikan status HTTP yang terlihat normal?”

- **Pengguna awal:** solo backend developer / small startup QA.
- **Input:** OpenAPI 3.x (JSON pada MVP), daftar business rules singkat, URL API sandbox/lokal yang developer miliki.
- **Output:** test plan terstruktur, hasil eksekusi request nyata, failure report dengan expected vs actual dan langkah reproduksi.
- **Value proposition:** penulisan tes untuk aturan bisnis sederhana jadi lebih mudah dan findings lebih dapat ditindaklanjuti.
- **Pesaing/alternatif:** pytest manual, Postman, Schemathesis. **Jangan mengklaim API testing otomatis baru**; angle yang dihipotesiskan adalah *natural-language business-rule-to-executable-test* yang dibatasi dan dapat diaudit.
- **Tidak membuktikan:** keamanan aplikasi secara menyeluruh, semua bug, semua business logic, atau kebenaran sistem secara absolut.

## 4. NORTH STAR DAN DEFINITION OF DONE

**Demo hero:** API withdraw demo sengaja memiliki bug overdraft. OpenAPI valid, tetapi rule “withdraw amount must not exceed balance” dilanggar. AI menghasilkan tes overdraft, runner menjalankannya, report menunjukkan evidence aktual.

**MVP features — hanya 4 modul inti:**
1. OpenAPI parser: daftar path/method sederhana, menolak spesifikasi invalid.
2. Muse Spark test planner: aturan bisnis + spesifikasi → keluaran Pydantic terstruktur; ada **offline fixture** yang diberi label eksplisit, bukan hasil AI.
3. Safe test executor: hanya target berizin dan allowlisted; bounded methods, jumlah tests, timeout; tak boleh scan arbitrary public URLs.
4. Evidence view: result PASS / FAIL / ERROR / NOT_RUN, expected vs actual, request sederhana yang dapat direproduksi; redact secrets.

**Demo must pass:** secara lokal satu happy-path PASS dan satu negative scenario FAIL terhadap API demo; kesimpulan sesuai actual response; tombol simulasi tidak boleh disamarkan sebagai live AI.

## 5. ARCHITECTURE DECISIONS — BERSIFAT WAJIB

- Stack: Python 3.11+, FastAPI, Pydantic, HTTPX, pytest, Streamlit, OpenAI-compatible SDK dengan **Meta base URL**.
- 1 intelligent planner + deterministic runner, **bukan** multi-agent swarm / autonomous code repair.
- Config melalui `.env`, jangan hardcode token; `.env`, log berisi credential, screenshot sensitif harus diignore.
- Response model harus tervalidasi schema. Model menjelaskan **test design**, tidak menentukan status PASS/FAIL secara subjektif.
- Semua IO eksternal melalui adapter dengan timeout dan error handling; kalau Meta API gagal: **tampilkan status API unavailable**, jangan diam-diam mengaku online.
- Mode fixture untuk testing lokal (tanpa key) harus jelas: `META_MODE=fixture`.
- Permission boundaries: default hanya loopback host dan port tertentu; request execution harus explicit consent. Tidak ada auto-follow redirects; batasi jumlah requests, metode dan body.
- Tidak mengirim token, password, API key, atau data user sensitif kepada model/log.
- Prioritaskan determinisme, reproducibility dan error messages daripada animasi premium.

## 6. PENGAMBILAN KEPUTUSAN: CHATGPT vs CODEX

**ChatGPT harus:**
- Mengurai setiap kebutuhan menjadi task kecil dan acceptance criteria.
- Mengecek kecocokan dengan R0 dan 7 aspek: rules, problem & impact, innovation, business value, working execution, feasibility/scalability, storytelling.
- Menolak fitur yang tidak meningkatkan keberhasilan demo atau bukti dalam 10 hari.
- Mereview laporan Codex: diff, test command, hasil real, unresolved risk, next smallest step.
- Jika ada asumsi tidak terverifikasi, beri label `[ASSUMPTION]` atau `[PENDING RULE]`.

**Codex harus:**
- Baca `AGENTS.md`, docs, dan source code sebelum membuat perubahan.
- Implementasikan **satu acceptance target per task**, bukan mengerjakan semua backlog dalam satu prompt.
- Gunakan test-first bila relevan, minimal test untuk failure condition.
- Jalankan test/format/lint yang tersedia; laporkan PASS/FAIL/NOT RUN jujur.
- Tulis daftar file berubah, ringkasan diff, bukti/command pengujian, risiko dan langkah berikutnya.
- STOP jika memerlukan biaya, izin network eksekusi, public deploy, penghapusan data, atau perubahan scope; minta izin.

**Project owner:** menerima/reject tradeoffs, menyediakan API key secara lokal, memutuskan release/deploy.

## 7. BUILD GATES DAN RITME 10 HARI

| Gate | Target | Evidence wajib |
|---|---|---|
| R0 | Setelah Official Rules tersedia | aturan final tercatat, konflik diidentifikasi |
| G1 | Hari 1 | repo, venv, test suite + health endpoint berjalan |
| G2 | Hari 2 | demo API (bug disengaja) + OpenAPI parse |
| G3 | Hari 3–4 | integrasi Meta yang diverifikasi live; structured test plan terparse |
| G4 | Hari 5–6 | test execution bounded + actual evidence |
| G5 | Hari 7 | UI end-to-end dan 1 PASS / 1 FAIL di demo |
| G6 | Hari 8 | baseline vs AI + metrik dengan dataset test yang sama |
| G7 | Hari 9 | demo video, README, error states, repo hygiene |
| G8 | Hari 10 | final audit Official Rules + submission artifacts |

**Stop conditions:** Jika hari ke-4 Meta key belum tersedia, kerjakan fixture untuk memvalidasi alur tetapi **jangan submit seolah integrasi Meta sudah nyata**. Eskalasikan akses ke project owner. Jika hari ke-6 runner belum aman dan stabil, potong features (bukan longgarkan safeguards). Jika hari ke-8 belum ada evidence reproducible, prioritaskan reliability ketimbang styling.

## 8. BENCHMARK MINIMUM (TANPA KLAIM PALSU)

- Baseline: tes sederhana hasil OpenAPI/hand-written standardized checks (misalnya 1 happy path + 1 invalid schema); definisikan tepat kasusnya.
- AI variant: tes yang diturunkan dari natural-language rule, setelah direview eligibility dan ekspektasinya.
- Metrik: test cases generated, valid test case rate, unique injected faults found, false positives, runtime, API/model costs jika tersedia.
- **Jangan mencampur fixture dengan Meta inference**; laporkan terpisah.
- Gunakan seeded demo faults agar perbandingan repeatable. Jangan fabrikasi angka atau menyajikan simulasi sebagai real-world incident.
- Jika perbandingan tidak mendukung keunggulan AI, ungkapkan apa adanya.

## 9. UI / DEMO PRINCIPLES DARI PROMPT ASLI

- Cerita 60–90 detik: *'200 OK, but the withdrawal broke the rule.'*
- Tampilan utama: **OpenAPI + business rule → generated tests → evidence**.
- Side-by-side: basic schema checks versus rule-aware test cases (dengan sumber jelas).
- Visual: one accent, high contrast, typography rapi, execution states jelas; prioritas keterbacaan > Awwwards styling.
- DILARANG fake testimonials, fake usage stats, demo pre-recorded diklaim live, wow-factor berupa gimmick Three.js yang menghabiskan waktu.
- Responsif desktop dulu, mobile usable; aksesibilitas dasar seperti label, kontras, keyboard focus.

## 10. FITUR DILARANG DALAM MVP

- Autonomously mutate arbitrary production systems, payment real money, security exploit scanning, SSRF unrestricted.
- Multi-agent platform, CI/CD SaaS, browser agent, IDE extension, OAuth + billing, database cloud kompleks.
- Training/fine-tuning model sendiri, 3D animation, landing page mewah yang tidak membantu demo.
- Janji 100% bug detection, 'production ready', keamanan tersertifikasi, atau novelty absolut tanpa bukti.

## 11. TEMPLATE PERINTAH KE CODEX

```text
Baca AGENTS.md, docs/PROJECT_FRAMEWORK.md, docs/RULES_COMPLIANCE.md, dan docs/CODEX_TASKS.md.
Kerjakan HANYA Task [ID] yang saya tunjukkan.
Scope dan acceptance criteria harus dipatuhi; jangan menambah fitur di luar task.
Lakukan perubahan sekecil mungkin, tambahkan/ubah tests, lalu jalankan tests.
Jangan mengakses layanan publik, mem-push repo, membuka billing, atau mempublikasikan deployment tanpa izin.
Laporkan: (1) file berubah, (2) test command & result, (3) evidence,
(4) risiko, (5) saran task berikutnya. Jangan klaim selesai kalau tests belum lulus.
```

## 12. TEMPLATE LAPORAN HARIAN DAN REVIEW

```text
DAY / GATE:
TASK:
R0 status: PASS / PENDING / BLOCKED
What changed:
Demo behavior (observed, not claimed):
Tests run + exact results:
Meta mode used: live / fixture / unavailable
Risks / blockers:
Decision needed from project owner:
Next smallest task:
```

## 13. CRITICAL REVIEW / GO-NO GO

Setiap deliverable perlu ditantang:
- Apakah model Meta benar-benar diperlukan untuk tugas ini atau rule mapping deterministik sudah cukup?
- Apakah expected behavior punya sumber spesifikasi/rule tepercaya, bukan imajinasi AI?
- Apakah test execution benar-benar terjadi, dan ada bukti?
- Apakah hasil bisa diulang oleh juri?
- Apakah produk lebih dari ChatGPT wrapper karena terhubung ke eksekusi/validasi nyata?
- Apakah proyek sesuai rules final, tidak sekadar kesesuaian tema?

**Keputusan sekarang:** `CONDITIONAL GO` untuk ide; `R0 PENDING` sampai official rules final diverifikasi; demo MVP dan scope disetujui.
