# TASK 01 — Bootstrap and smoke evidence

Tanggal: 26 Oktober 2026 (Asia/Jakarta).

Task: hanya 01. Instruksi AGENTS, master prompt, compliance register, framework,
dan task board sudah dibaca. R0 tetap PENDING.

Files changed:
- `tests/test_bootstrap.py`: dua tes bootstrap offline.
- `docs/TASK_01_REPORT.md`: laporan ini.
- `.venv/`: environment, script smoke sementara, dan log lokal; diabaikan git.

Behavior implemented:
- Tidak ada perubahan source aplikasi, dependensi yang dideklarasikan, kredensial,
  atau guardrail. Tidak ditemukan error kode bootstrap.
- Tes memastikan health melaporkan fixture dan Streamlit memuat label fixture
  tanpa exception. AppTest tidak menekan tombol generate/execute.

## Commands and observed results

Semua perintah dijalankan dari root repository dengan PowerShell.

```powershell
python --version
```
```text
Python 3.11.9
```

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Pembuatan venv berhasil. Instalasi pertama gagal dalam sandbox:
```text
[WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions
ERROR: Could not find a version that satisfies the requirement fastapi<1,>=0.110 (from versions: none)
ERROR: No matching distribution found for fastapi<1,>=0.110
```

Perintah install yang sama diulang dengan akses network yang disetujui otomatis,
tetapi unduhan Streamlit mengalami timeout (exit 1):
```text
pip._vendor.urllib3.exceptions.ReadTimeoutError: HTTPSConnectionPool(host='files.pythonhosted.org', port=443): Read timed out.
```

Percobaan berikutnya berhasil (exit 0):
```powershell
.\.venv\Scripts\python.exe -m pip install --timeout 120 --retries 3 -r requirements.txt
```

Versi langsung yang terpasang, diverifikasi dengan perintah berikut:
```powershell
.\.venv\Scripts\python.exe -c "from importlib.metadata import version; print('\n'.join(f'{p}=={version(p)}' for p in ['fastapi','uvicorn','pydantic','httpx','python-dotenv','pytest','openai','streamlit']))"
```
```text
fastapi==0.162.0
uvicorn==0.54.0
pydantic==2.14.1
httpx==0.28.1
python-dotenv==1.2.4
pytest==9.1.1
openai==2.54.0
streamlit==1.66.1
```

```powershell
.\.venv\Scripts\python.exe -m pip check
```
```text
No broken requirements found.
```

```powershell
$env:META_MODE='fixture'
.\.venv\Scripts\python.exe -m pytest -q 2>&1 | Tee-Object -FilePath .venv/task01-pytest.txt
exit $LASTEXITCODE
```
```text
................                                                         [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  D:\Hackathon\API-Sentinel-AI\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
16 passed, 1 warning in 7.89s
```

Exit 0. Tidak ada perubahan dependensi untuk menghilangkan warning.

## Socket smoke test

Script sementara `.venv/task01_smoke.py` menjalankan tiga subprocess, memakai
HTTPX `trust_env=False`, `follow_redirects=False`, timeout 3 detik, menunggu startup,
memeriksa status/body, dan menghentikan prosesnya sendiri di blok `finally`.
Environment subprocess: `META_MODE=fixture`,
`ALLOWED_TEST_ORIGINS=http://127.0.0.1:8001`.

Percobaan pertama:
```powershell
.\.venv\Scripts\python.exe .venv/task01_smoke.py 2>&1 | Tee-Object -FilePath .venv/task01-smoke.txt
exit $LASTEXITCODE
```

Exit 1. Log controller:
```text
ERROR:    [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000): only one usage of each socket address (protocol/network address/port) is normally permitted
```

Request health berakhir dengan `httpx.ReadTimeout: timed out`. Demo dan UI sempat
startup, lalu semua subprocess milik smoke test dihentikan. Pemeriksaan awal
`Get-NetTCPConnection` tidak menghasilkan listener; `netstat -ano -p tcp`
kemudian memperlihatkan port 8000 digunakan PID 5452. Pemeriksaan proses:
```powershell
Get-Process -Id 5452 | Select-Object Id,ProcessName
```
```text
  Id ProcessName
  -- -----------
5452 svchost
```

Proses tersebut tidak dihentikan. Script sementara diubah memakai controller
8002 dan `CONTROLLER_URL=http://127.0.0.1:8002`; target demo tetap 8001.

```powershell
.\.venv\Scripts\python.exe .venv/task01_smoke.py 2>&1 | Tee-Object -FilePath .venv/task01-smoke-retry.txt
exit $LASTEXITCODE
```

Exit 0. Perintah layanan dan hasil HTTP berikut berasal dari script tersebut:
```text
START: python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8002
START: python -m uvicorn backend.app.demo_api:app --host 127.0.0.1 --port 8001
START: python -m streamlit run ui/streamlit_app.py --server.address=127.0.0.1 --server.port=8501 --server.headless=true --browser.gatherUsageStats=false
GET http://127.0.0.1:8002/health -> 200 {"status":"ok","mode":"fixture"}
GET http://127.0.0.1:8001/openapi.json -> 200 title=Synthetic Wallet API � intentionally buggy
GET http://127.0.0.1:8501/_stcore/health -> 200 ok
GET http://127.0.0.1:8501/ -> 200 HTML received
POST http://127.0.0.1:8001/withdraw balance=100 amount=50 -> 200 {"approved":true,"remaining":50}
POST http://127.0.0.1:8001/withdraw balance=100 amount=150 -> 200 {"approved":true,"remaining":-50}
STOP: all smoke-test processes stopped
```

Karakter pengganti pada title berasal dari encoding output terminal; respons
OpenAPI berhasil diparse sebagai JSON. Ini bukan hasil Meta inference atau
evaluasi runner; dua POST di atas hanya smoke endpoint demo sintetis.

## Acceptance criteria

| Kriteria TASK 01 | Hasil |
|---|---|
| Python 3.11+ dan requirements terpasang | PASS; 3.11.9, pip check bersih |
| Seluruh tes lulus | PASS; 16 passed, 1 warning |
| Controller `/health` 200 | PASS pada port alternatif 8002; port default 8000 terhalang |
| Demo API startup lokal | PASS; OpenAPI dan dua POST merespons 200 |
| UI startup dan menampilkan model mode | PASS; HTTP 200 dan AppTest memverifikasi label fixture |

Meta inference: NOT RUN. Mode aplikasi untuk verifikasi: FIXTURE.
Tidak ada panggilan layanan model, deployment, atau push GitHub.

Remaining issues:
- Port default 8000 digunakan proses sistem; verifikasi controller dilakukan pada
  8002. Untuk menjalankan ulang di komputer ini, gunakan perintah controller
  di atas dan set `$env:CONTROLLER_URL='http://127.0.0.1:8002'` pada terminal UI.
- Satu deprecation warning TestClient tetap ada.
- Pemeriksaan UI memakai AppTest dan HTTP, bukan inspeksi browser manual.
- Live Meta dan alur generate/execute melalui UI tidak diverifikasi pada TASK 01.
- Seluruh scaffold sudah untracked saat mulai; `git diff` tidak dapat digunakan
  untuk menyimpulkan file-file tersebut dibuat dalam task ini.

Next recommended task: TASK 02, setelah instruksi owner; tidak dikerjakan di sini.
