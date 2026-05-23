# 🧬 Folliscope — Early-Warning Hair-Loss Risk Assessment

> **Berbasis Computational Biology** | Integrated genetic & clinical analysis with live NCBI reference

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green.svg)](https://fastapi.tiangolo.com)
[![Biopython](https://img.shields.io/badge/Biopython-1.83-orange.svg)](https://biopython.org)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg)](https://docker.com)
[![Tests](https://img.shields.io/badge/tests-66%20passing-brightgreen.svg)](tests/test_folliscope.py)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> ⚠️ **DISCLAIMER:** Folliscope adalah proyek edukasi untuk mata kuliah Computational Biology dan **BUKAN** alat diagnostik klinis. Hasilnya tidak menggantikan konsultasi dengan dokter atau dermatolog berlisensi. Lihat [METHODS.md](METHODS.md) untuk pembahasan lengkap tentang batasan ilmiah.

---

## Fitur Utama

- 🧬 **Phenotype-to-genotype inference** — estimasi rentang CAG repeat dari kuesioner klinis, untuk user yang tidak punya data DNA
- 📡 **Live NCBI integration** — fetch sekuens referensi AR (NM_000044.6) dari NCBI RefSeq setiap analisis, bandingkan dengan profil user
- 🔬 **Hybrid PRS scoring** — gabungkan data genetik (FASTA / SNP / 23andMe) + kuesioner klinis 5 bagian
- 🎯 **Transparent confidence** — laporkan tingkat keyakinan analisis: 70% (kuesioner saja) → 85% (+ SNP) → 95% (+ DNA)
- 🧪 **Treatment scenario simulator** — slider interaktif untuk lihat dampak perubahan gaya hidup terhadap skor risiko
- 📄 **Structured PDF report** — laporan terstruktur dengan gauge, NCBI comparison, dan rekomendasi
- 🚀 **Deploy-ready** — siap deploy ke Render / Railway / Fly.io dengan satu klik
- ✅ **66 unit tests** — semua komponen scoring tervalidasi

---

## Daftar Isi

1. [Latar Belakang Ilmiah](#latar-belakang-ilmiah)
2. [Arsitektur Sistem](#arsitektur-sistem)
3. [Formula Risk Score Hybrid](#formula-risk-score-hybrid)
4. [Database SNP dan Referensi](#database-snp-dan-referensi)
5. [Instalasi](#instalasi)
6. [Cara Menjalankan](#cara-menjalankan)
7. [Deploy ke Internet](#deploy-ke-internet)
8. [Cara Menggunakan](#cara-menggunakan)
9. [Penjelasan Kuesioner Medis](#penjelasan-kuesioner-medis)
10. [Contoh Penggunaan API](#contoh-penggunaan-api)
11. [Struktur Proyek](#struktur-proyek)
12. [Menjalankan Tests](#menjalankan-tests)
13. [Cara Memperluas Folliscope](#cara-memperluas-folliscope)
14. [Limitasi dan Disclaimer](#limitasi-dan-disclaimer)
15. [Referensi Literatur](#referensi-literatur)

> 💡 Lihat juga [METHODS.md](METHODS.md) untuk pembahasan ilmiah lengkap: apa yang divalidasi vs. apa yang merupakan design choice.

---

## Latar Belakang Ilmiah

### Androgenetic Alopecia (AGA)

**Androgenetic Alopecia (AGA)** adalah bentuk kebotakan paling umum pada manusia, mempengaruhi sekitar 50% pria di atas usia 50 tahun dan 25-40% wanita sepanjang hidupnya. AGA disebabkan oleh interaksi antara faktor genetik dan hormonal, terutama hormon **dihidrotestosteron (DHT)**.

**Mekanisme Utama:**
1. Enzim **5α-reduktase tipe 2** (dikode gen *SRD5A2*) mengkonversi testosteron → DHT di folikel rambut kulit kepala
2. DHT berikatan dengan **Androgen Receptor (AR)** di sel papilla dermal
3. Kompleks DHT-AR mengaktifkan program transkripsi yang memperpendek fase anagen (pertumbuhan)
4. Folikel mengalami **miniaturisasi progresif** — rambut semakin tipis, pendek, hingga berhenti tumbuh

### Gen AR — Target Utama

Gen **AR** (Androgen Receptor) adalah gen kunci dalam patogenesis AGA:

| Parameter | Nilai |
|-----------|-------|
| Lokasi Kromosom | Xq12 (kromosom X, X-linked) |
| NCBI Gene ID | 367 |
| RefSeq mRNA | NM_000044.6 |
| Ukuran Protein | 919 asam amino |

**Signifikansi X-Linked:** Karena AR terletak di kromosom X, pria mewarisi satu-satunya salinan AR dari ibu mereka. Ibu mewarisi kromosom X dari ayahnya (kakek dari sisi ibu). Inilah mengapa **kakek dari pihak ibu yang botak** adalah prediktor paling kuat untuk risiko kebotakan pada cucu laki-laki.

### CAG Repeat Polymorphism

Exon 1 gen AR mengandung sekuens trinukleotida **(CAG)n** yang mengkode poliglutamin (polyQ). Panjang repeat ini bervariasi antar individu dan menentukan sensitivitas reseptor AR terhadap DHT:

| CAG Repeats | Kategori Risiko | Mekanisme |
|-------------|-----------------|-----------|
| < 18 | SANGAT TINGGI | Reseptor sangat sensitif DHT |
| 18 – 21 | TINGGI | Sensitivitas AR tinggi |
| 22 – 24 | SEDANG | Sensitivitas moderat |
| 25 – 29 | RENDAH | Sensitivitas rendah |
| ≥ 30 | PROTEKTIF | Efek protektif |

> Referensi: Choong et al. 1996; Hillmer et al. 2005 (Am J Hum Genet)

---

## Arsitektur Sistem

```
Input Data
    │
    ├─── FASTA Sekuens DNA ──► Regex CAG/GGN Counter ──► GeneticScore
    │                                                           │
    ├─── TSV Genotype SNP ───► SNP Comparator ────────────────►│
    │                                                           │
    └─── Kuesioner Klinis ──► ClinicalScorer ─────────────────►│
          (5 Bagian)               │                            │
                                   ├── FamilyScore             │
                                   └── LifestyleScore          │
                                                                ▼
                                                     HybridPRSCalculator
                                                                │
                                                                ▼
                                               RiskScore (0–100) + Kategori
                                                                │
                                                                ▼
                                                    Rekomendasi Medis
```

**Stack Teknologi:**
- **Backend:** Python 3.10+, FastAPI, Pydantic v2
- **Bioinformatika:** Regex-based CAG/GGN counter (Biopython available)
- **Frontend:** HTML5 + CSS3 + Vanilla JavaScript
- **Visualisasi:** Chart.js (Radar, Bar, SNP Heatmap)
- **API:** REST JSON endpoints

---

## Formula Risk Score Hybrid

### Mode Hybrid (Genetik + Klinis)

```
HybridScore = 0.45 × GeneticScore + 0.30 × ClinicalScore + 0.15 × FamilyScore + 0.10 × LifestyleScore
```

Setelah itu dikali **age modifier**:
- Usia < 25 tahun: × 1.15 (onset sangat dini = sinyal genetik kuat)
- Usia 25–29 tahun: × 1.08
- Usia ≥ 50 tahun: × 0.90

### Mode Klinis Saja (Tanpa DNA)

```
ClinicalOnlyScore = 0.55 × ClinicalScore + 0.30 × FamilyScore + 0.15 × LifestyleScore
```

### Komponen GeneticScore (0–100)

```
GeneticScore = 0.40 × CagScore + 0.15 × GgnScore + 0.45 × SNPScore
```

- **CagScore:** Berdasarkan threshold Choong 1996 (CAG < 18 → 100, ≥ 30 → 10)
- **GgnScore:** Berdasarkan threshold GGN (< 18 → 75, ≥ 24 → 20)
- **SNPScore:** Normalized sum dari PRS weight × (OR − 1) untuk tiap SNP risiko

### Komponen ClinicalScore (0–100)

| Sub-komponen | Bobot | Sumber |
|--------------|-------|--------|
| Skala Norwood/Ludwig | 35% | Norwood 1975, Ludwig 1977 |
| Pola kerontokan + area | 20% | ALOPHA Index |
| Hair Pull Test | 15% | Standar klinis |
| Volume rontok/hari | 10% | Telogen effluvium criteria |
| Miniaturisasi (diameter) | 10% | Trichoscopy criteria |
| Durasi gejala | 10% | Chronicity of AGA |

### Komponen FamilyScore (0–100)

| Anggota Keluarga | Bobot | Alasan |
|------------------|-------|--------|
| **Kakek dari ibu** | **35%** | **AR X-linked: paling berpengaruh** |
| Ayah | 25% | Autosomal + X interaction |
| Kakek dari ayah | 15% | Pengaruh lebih lemah |
| Saudara laki-laki | 10% | Shared genetics |
| Ibu (penipisan) | 8% | X carrier |
| Jumlah generasi | 7% | Penetrance estimation |

### Komponen LifestyleScore (0–100)

| Faktor | Bobot | Mekanisme |
|--------|-------|-----------|
| Komorbiditas (PCOS, metabolik) | 25% | Gangguan hormonal langsung |
| Stres | 25% | Stres → kortisol → androgen ↑ |
| Merokok | 20% | Vasokonstriksi folikel |
| Diet & Olahraga | 15% | Nutrisi folikel |
| Tidur | 15% | Disrupsi ritme hormonal |

### Kategori Risiko Final

| Skor | Kategori | Warna |
|------|----------|-------|
| 0–19 | MINIMAL | Hijau (#2ecc71) |
| 20–39 | RENDAH | Hijau tua (#27ae60) |
| 40–59 | SEDANG | Oranye (#f39c12) |
| 60–79 | TINGGI | Merah oranye (#e67e22) |
| 80–100 | SANGAT TINGGI | Merah (#e74c3c) |

---

## Database SNP dan Referensi

| rs ID | Gen | Chr | Alel Risiko | OR | Bobot PRS |
|-------|-----|-----|-------------|-----|-----------|
| rs6152 | AR | X | G | 2.50× | 0.90 |
| rs1385699 | EDA2R | X | C | 2.20× | 0.85 |
| rs12558842 | AR | X | G | 1.80× | 0.70 |
| rs2497938 | AR | X | C | 1.75× | 0.65 |
| rs1160312 | PAX1/FOXA2 | 20 | A | 1.60× | 0.60 |
| rs7349332 | WNT10A | 2 | T | 1.45× | 0.50 |
| rs523349 | SRD5A2 | 2 | G | 1.40× | 0.55 |
| rs9479482 | HDAC9 | 7 | C | 1.35× | 0.45 |
| rs929626 | EBF1 | 5 | C | 1.30× | 0.35 |

---

## Instalasi

### Cara Tercepat — Docker (Direkomendasikan)

Tidak perlu install Python atau dependencies apapun, cukup punya **Docker Desktop**.

```bash
# Clone proyek
git clone <repo-url>
cd folliscope

# Build dan jalankan (sekali perintah)
docker compose up --build
```

Buka browser: **http://localhost:8000**

Untuk menjalankan berikutnya (tanpa build ulang):
```bash
docker compose up
```

Matikan server:
```bash
docker compose down
```

> Pastikan **WSL Integration** aktif di Docker Desktop → Settings → Resources → WSL Integration.

---

### Cara Manual (Tanpa Docker)

#### Prasyarat

- Python 3.11 atau lebih baru
- pip (Python package manager)
- Git (opsional)

### Windows

```bash
# 1. Clone atau download proyek
git clone <repo-url>
cd folliscope

# 2. Buat virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

### macOS / Linux

```bash
# 1. Clone proyek
git clone <repo-url>
cd folliscope

# 2. Buat virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Cara Menjalankan

### Dengan Docker

```bash
docker compose up --build   # pertama kali / setelah ada perubahan kode
docker compose up           # berikutnya
docker compose down         # matikan
```

### Mode Development (dengan auto-reload)

```bash
# Aktifkan virtual environment terlebih dahulu
source venv/bin/activate          # Linux/macOS
# atau
venv\Scripts\activate             # Windows

# Jalankan server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Buka browser: **http://localhost:8000**

### Mode Production

```bash
# Dengan 4 worker processes
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Dengan Python langsung

```bash
python main.py
```

### Verifikasi instalasi

```bash
curl http://localhost:8000/api/health
# → {"status":"ok","service":"Folliscope API","timestamp":"..."}
```

---

## Deploy ke Internet

Folliscope siap deploy ke beberapa PaaS gratis. Dockerfile sudah memakai `$PORT` env var,
jadi image yang sama jalan di mana saja.

### 🚀 Render.com (paling mudah, free tier)

1. Push repo ke GitHub
2. Buka [dashboard.render.com](https://dashboard.render.com) → **New** → **Blueprint**
3. Pilih repo ini — Render akan baca `render.yaml` otomatis
4. Tunggu ~5 menit build → URL public siap pakai

Health check di `/api/health` otomatis di-monitor. Auto-deploy nyala saat push ke `main`.

### 🚂 Railway.app

1. `npm i -g @railway/cli`
2. `railway login && railway init && railway up`
3. Atau via dashboard: connect repo, Railway auto-detect Dockerfile + `railway.json`

### ✈️ Fly.io (terdekat ke Indonesia — region `sin` Singapura)

```bash
# Sekali set up:
curl -L https://fly.io/install.sh | sh
fly auth signup
fly launch --copy-config --no-deploy
fly deploy

# Update berikutnya:
fly deploy
```

`fly.toml` sudah dikonfigurasi dengan `auto_stop_machines` jadi tetap di free tier.

### 🐳 Docker self-host (VPS / Cloud Run / dll)

```bash
docker build -t folliscope .
docker run -p 8000:8000 -e PORT=8000 folliscope
```

---

## Cara Menggunakan

### Antarmuka Web

1. **Buka** `http://localhost:8000`
2. **Klik "Mulai Analisis"** untuk ke halaman analisis
3. **Tab "Analisis Klinis" (wajib):**
   - Isi 5 bagian kuesioner secara berurutan menggunakan tombol "Lanjut"
   - Klik "Analisis Sekarang" di bagian terakhir
4. **Tab "Analisis Genetik" (opsional):**
   - Upload file FASTA exon 1 gen AR, atau paste sekuens langsung
   - Pilih genotype untuk 9 SNP secara manual, atau upload file TSV
   - Gunakan tombol "Sample Data" untuk mencoba dengan data contoh
5. **Tab "Hasil Analisis":**
   - Lihat skor risiko, kategori, dan rekomendasi
   - Klik "Unduh Laporan" untuk menyimpan hasil

### Menggunakan Sample Data

File contoh tersedia di folder `sample_data/`:

```bash
# Profil sangat tinggi: CAG=17, GGN=23, semua SNP risiko
sample_data/high_risk_sample.fasta
sample_data/high_risk_genotype.tsv

# Profil sedang: CAG=23, GGN=22, 5 SNP risiko
sample_data/medium_risk_sample.fasta
sample_data/medium_risk_genotype.tsv

# Profil rendah: CAG=29, GGN=20, 2 SNP risiko
sample_data/low_risk_sample.fasta
sample_data/low_risk_genotype.tsv

# Profil protektif: CAG=33, GGN=18
sample_data/protective_sample.fasta
```

### Format File FASTA

```fasta
>header_opsional | deskripsi
ATGCTTCAGCAGCAGCAGCAGCAGCAGCAGCAGCAGCAGCAGCAGCAGCAG
GGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGC
```

- Header dimulai dengan `>`
- Sekuens hanya berisi karakter ATCG (N diizinkan)
- Mengandung setidaknya 5 CAG consecutive untuk terdeteksi

### Format File TSV Genotype SNP

```tsv
# Komentar diawali #
rs6152	G
rs1385699	C
rs12558842	G
rs2497938	C
rs7349332	T
rs9479482	C
rs1160312	A
rs929626	C
rs523349	G
```

- Dua kolom: `rs_id` TAB `allele`
- Allele dalam format single-letter (A, T, C, atau G)
- SNP yang tidak ada di file dianggap "tidak diketahui"

---

## Penjelasan Kuesioner Medis

### Bagian 1: Demografi

| Input | Penjelasan |
|-------|------------|
| Usia | Onset dini (< 25 tahun) menunjukkan komponen genetik yang kuat |
| Jenis Kelamin | Menentukan skala yang digunakan (Norwood untuk pria, Ludwig untuk wanita) |
| Etnis | Prevalensi AGA bervariasi: Kaukasian > Asia > Afrika |
| Usia Pubertas | Pubertas dini = paparan androgen lebih lama = faktor risiko tambahan |

### Bagian 2: Gejala Kerontokan

| Input | Normal | Abnormal |
|-------|--------|----------|
| Rontok per hari | 50–100 helai | > 150 helai |
| Durasi | < 1 bulan | > 6 bulan (kronis) |
| Pola | Difus/tidak ada | M-shape atau vertex = AGA klasik |
| Diameter | Tidak berubah | Mengecil = miniaturisasi = hallmark AGA |
| Norwood (pria) | I–II | III–VII (semakin parah) |
| Ludwig (wanita) | I | II–III (semakin parah) |

### Bagian 3: Hair Pull Test

Instruksi standar klinis:
1. Ambil sekelompok ~60 helai rambut dengan jari
2. Tarik perlahan dari pangkal menuju ujung
3. Hitung rambut yang tercabut

| Hasil | Interpretasi |
|-------|-------------|
| ≤ 3 rambut | Normal |
| 4–6 rambut | Borderline |
| > 6 rambut | Aktif rontok (telogen effluvium atau AGA aktif) |

### Bagian 4: Riwayat Keluarga

Pembobotan berdasarkan mekanisme pewarisan X-linked:

- **Kakek dari ibu (35%):** Paling penting. Pria warisi AR dari ibu, ibu dari ayahnya
- **Ayah (25%):** Penting untuk komponen autosomal dan interaksi kompleks
- **Onset dini (<30 tahun):** Multiplier risiko 1.15–1.20×

### Bagian 5: Gaya Hidup & Kesehatan

| Faktor | Mekanisme Risiko |
|--------|-----------------|
| Stres tinggi | Kortisol → inhibisi fase anagen, meningkatkan DHT |
| Tidur < 6 jam | Disrupsi ritme sirkadian hormonal |
| Merokok | Vasokonstriksi folikel, kerusakan oksidatif |
| PCOS | Hiperandrogenisme langsung |
| Gangguan tiroid | Hipotiroid → telogen effluvium |
| Defisiensi besi | Ferritin rendah = insufisiensi nutrisi folikel |
| Kekurangan Vitamin D | Terkait gangguan siklus folikel |

---

## Contoh Penggunaan API

### Health Check

```bash
curl http://localhost:8000/api/health
```

```json
{"status": "ok", "service": "Folliscope API", "timestamp": "2024-01-01T12:00:00"}
```

### Dapatkan Database SNP

```bash
curl http://localhost:8000/api/snp-database
```

### Analisis Lengkap (Hybrid)

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "genetic_data": {
      "fasta_sequence": ">test\nCAGCAGCAGCAGCAGCAGCAGCAGCAGCAGCAGCAGCAGCAGCAGCAGCAGGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGCGGC",
      "snp_genotypes": {"rs6152": "G", "rs1385699": "C", "rs12558842": "G"}
    },
    "section1": {"age": 28, "gender": "male", "ethnicity": "Asia"},
    "section2": {
      "hair_loss_per_day": 200, "loss_duration_months": 12,
      "loss_pattern": "m-shape", "thinning_areas": ["hairline", "crown"],
      "thinning_perception": 7, "diameter_decreased": true, "norwood_scale": 4
    },
    "section3": {"hair_pull_count": 10},
    "section4": {
      "father_bald": true, "father_bald_age": 35,
      "maternal_grandfather_bald": true, "generations_bald": 2
    },
    "section5": {
      "stress_level": 8, "sleep_hours": 5.5,
      "smoking": false, "diet_quality": "balanced",
      "exercise_frequency": "light"
    }
  }'
```

**Contoh Respons (disingkat):**

```json
{
  "success": true,
  "analysis_type": "hybrid",
  "scores": {
    "hybrid_score": 72.4, "genetic_score": 78.0,
    "clinical_score": 65.3, "family_score": 68.0, "lifestyle_score": 48.2
  },
  "risk_category": "TINGGI",
  "risk_category_label": "High",
  "confidence": {
    "level": "questionnaire_plus_dna", "label": "Questionnaire + DNA sequence",
    "percent": 95, "description": "Direct measurement of your AR CAG repeats..."
  },
  "ncbi_reference": {
    "available": true, "source": "NCBI RefSeq",
    "accession": "NM_000044.6", "sequence_length": 10667,
    "cag_count": 22, "fetched_at": "2026-05-23T13:35:31"
  },
  "ncbi_comparison": {
    "ncbi_reference_cag": 22, "user_cag_midpoint": 18,
    "interpretation": "Your AR profile is moderately shorter than the NCBI reference..."
  },
  "recommendations": [
    "Warning: AGA risk is high — early intervention is strongly recommended.",
    "See a dermatologist within the next 1–3 months.",
    "..."
  ],
  "disclaimer": "This is an educational risk assessment, not a medical diagnosis..."
}
```

### Upload File FASTA

```bash
curl -X POST http://localhost:8000/api/analyze/fasta-upload \
  -F "file=@sample_data/high_risk_sample.fasta"
```

---

## Struktur Proyek

```
folliscope/
├── README.md                    ← Dokumentasi ini
├── METHODS.md                   ← Defensibilitas ilmiah & limitasi
├── CLAUDE.md                    ← Panduan untuk Claude Code AI
├── requirements.txt             ← Python dependencies
├── main.py                      ← Entry point FastAPI
│
├── Dockerfile                   ← Docker image (multi-stage, honors $PORT)
├── docker-compose.yml           ← Jalankan dengan `docker compose up`
├── render.yaml                  ← Deploy ke Render.com (Blueprint)
├── railway.json                 ← Deploy ke Railway.app
├── fly.toml                     ← Deploy ke Fly.io (region: Singapore)
├── .dockerignore                ← Exclude cache & venv dari Docker build
│
├── backend/
│   ├── __init__.py
│   ├── reference_data.py        ← SNP database, threshold, recommendations
│   ├── analyzer.py              ← CAG/GGN counter + SNP detector
│   ├── clinical_analyzer.py     ← Kuesioner scorer (5 sections)
│   ├── phenotype_inference.py   ← Phenotype → CAG estimate + confidence
│   ├── risk_score.py            ← Hybrid PRS calculator
│   ├── ncbi.py                  ← NCBI Entrez — live fetch AR reference (NM_000044.6)
│   ├── parser_23andme.py        ← Parser file raw data 23andMe
│   └── api.py                   ← REST endpoints (FastAPI Router)
│
├── frontend/
│   ├── index.html               ← Landing page
│   ├── analyze.html             ← Wizard form + results + treatment simulator
│   ├── about.html               ← Penjelasan ilmiah
│   ├── database.html            ← Database SNP interaktif
│   ├── css/
│   │   └── style.css            ← Design system v2 (Inter + Space Grotesk + JetBrains Mono)
│   └── js/
│       ├── api.js               ← HTTP client untuk backend
│       ├── charts.js            ← Chart.js visualizations
│       └── main.js              ← UI controller, form logic, PDF generator
│
├── sample_data/
│   ├── high_risk_sample.fasta   ← CAG=17, GGN=23 (very high)
│   ├── medium_risk_sample.fasta ← CAG=23, GGN=22 (moderate)
│   ├── low_risk_sample.fasta    ← CAG=29, GGN=20 (low)
│   ├── protective_sample.fasta  ← CAG=33, GGN=18 (protective)
│   ├── high_risk_genotype.tsv   ← Semua 9 SNP = alel risiko
│   ├── medium_risk_genotype.tsv ← 5 SNP risiko, 4 normal
│   └── low_risk_genotype.tsv    ← 2 SNP risiko, 7 normal
│
└── tests/
    ├── __init__.py
    └── test_folliscope.py        ← 66 unit tests (pytest)
```

---

## Menjalankan Tests

```bash
# Pastikan virtual environment aktif
source venv/bin/activate

# Jalankan semua tests
pytest tests/ -v

# Jalankan dengan coverage report
pytest tests/ -v --tb=short

# Jalankan test class tertentu
pytest tests/test_folliscope.py::TestCAGRepeats -v
pytest tests/test_folliscope.py::TestHybridRiskCalculation -v

# Jalankan test tunggal
pytest tests/test_folliscope.py::TestCAGRepeats::test_cag_17_count -v
```

**Target:** 66 test cases di 9 kelas pengujian:

| Kelas Test | Jumlah | Cakupan |
|-----------|--------|---------|
| `TestCAGRepeats` | 12 | Count, risk level, edge cases |
| `TestGGNRepeats` | 7 | Count, risk level, edge cases |
| `TestSNPDetection` | 8 | All risk, all normal, unknown, scoring |
| `TestClinicalScore` | 6 | Norwood, hair pull, bounds |
| `TestFamilyScore` | 4 | Weighting, zero, full history |
| `TestLifestyleScore` | 4 | High risk, healthy, bounds |
| `TestHybridRiskCalculation` | 11 | All 5 categories, hybrid vs clinical-only |
| `TestParsing` | 14 | FASTA multiline, TSV, edge cases |

---

## Cara Memperluas Folliscope

### Menambah SNP Baru

Edit `backend/reference_data.py`, tambahkan `SNPRecord` baru ke list `SNP_DATABASE`:

```python
SNPRecord(
    rs_id="rs12345678",
    gene="NAMA_GEN",
    chromosome="1",           # nomor kromosom
    risk_allele="A",          # allele yang meningkatkan risiko
    ref_allele="G",           # allele referensi normal
    odds_ratio=1.55,          # dari publikasi GWAS
    prs_weight=0.52,          # proposional terhadap ln(OR)
    description="Deskripsi singkat SNP",
    function="Fungsi biologis gen ini di folikel rambut"
),
```

Kemudian update `database.html` untuk menambahkan SNP ke tabel frontend.

### Mengubah Threshold CAG

Edit `CAG_THRESHOLDS` di `backend/reference_data.py`:

```python
CAG_THRESHOLDS = [
    (0, 17,   "SANGAT_TINGGI", 100, "Interpretasi..."),
    (18, 21,  "TINGGI",         80, "Interpretasi..."),
    # Tambah atau ubah baris di sini
]
```

### Mengubah Formula Risk Score

Edit bobot di `backend/risk_score.py`:

```python
def calculate_hybrid_score(genetic, clinical):
    g = genetic.genetic_score
    c = clinical.clinical_score
    f = clinical.family_score
    l = clinical.lifestyle_score
    # Ubah bobot di sini:
    score = 0.45 * g + 0.30 * c + 0.15 * f + 0.10 * l
    return score * clinical.age_modifier
```

### Menambah Rekomendasi

Edit dictionary `RECOMMENDATIONS` di `backend/reference_data.py` untuk menambah atau mengubah rekomendasi per kategori risiko.

---

## Limitasi dan Disclaimer

### Limitasi Ilmiah

1. **Panel SNP terbatas:** Folliscope menggunakan 9 SNP representatif. Studi GWAS terbaru (Heilmann-Heimbach 2017) mengidentifikasi >200 lokus yang berhubungan dengan AGA.

2. **Populasi referensi:** Threshold CAG/GGN didasarkan terutama pada studi populasi Kaukasian. Nilai cutoff mungkin sedikit berbeda untuk populasi Asia, Afrika, atau campuran.

3. **Simplifikasi model:** Formula PRS disederhanakan untuk tujuan edukasi. PRS klinis nyata menggunakan jutaan varian dengan bobot berbasis regresi logistik dari biobank besar.

4. **Tidak mempertimbangkan:** Interaksi gen-lingkungan (epistasis), ekspresi diferensial berdasarkan usia, atau efek haplotype.

5. **Self-report bias:** Data kuesioner klinis bergantung pada laporan subjektif pengguna.

6. **Belum divalidasi secara klinis:** Sistem ini belum diuji pada kohort pasien AGA yang terdiagnosis secara klinis.

### Disclaimer Etik

- ❌ Folliscope **BUKAN** alat diagnostik medis
- ❌ Hasil Folliscope **TIDAK** menggantikan pemeriksaan dermatologis
- ❌ **JANGAN** membuat keputusan medis berdasarkan output Folliscope semata
- ✅ Gunakan Folliscope sebagai **alat edukasi** tentang genetika AGA
- ✅ Selalu konsultasikan kondisi rambut dengan **dokter atau dermatolog berlisensi**

---

## Referensi Literatur

1. **Hillmer AM, et al. (2005).** Genetic variation in the human androgen receptor gene is the major determinant of common early-onset androgenetic alopecia. *Am J Hum Genet*, 77(1):140–148.

2. **Heilmann-Heimbach S, et al. (2017).** Meta-analysis identifies novel risk loci and yields systematic insights into the biology of male-pattern baldness. *Nat Commun*, 8:14694.

3. **Choong CS, et al. (1996).** Reduced androgen receptor gene expression with first exon CAG repeat expansion. *Mol Endocrinol*, 10(12):1527–1535.

4. **Ellis JA, et al. (2001).** Polymorphism of the androgen receptor gene is associated with male pattern baldness. *J Invest Dermatol*, 116(3):452–455.

5. **Prodi DA, et al. (2008).** EDA2R is associated with androgenetic alopecia. *J Invest Dermatol*, 128(9):2268–2270.

6. **Norwood OT. (1975).** Male pattern baldness: Classification and incidence. *South Med J*, 68(11):1359–1365.

7. **Ludwig E. (1977).** Classification of the types of androgenetic alopecia occurring in the female sex. *Br J Dermatol*, 97(3):247–254.

8. **Giovannucci E, et al. (1997).** The CAG repeat within the androgen receptor gene and its relationship to prostate cancer. *Proc Natl Acad Sci USA*, 94(7):3320–3323.

9. **Yip L, et al. (2009).** Gene-wide association study between the aromatase gene (CYP19A1) and female pattern hair loss. *Br J Dermatol*, 161(2):289–294.

---

## Lisensi

MIT License — untuk penggunaan edukasi dan non-komersial.

---

*Folliscope dibuat sebagai proyek UAS mata kuliah Computational Biology. Dibuat dengan ❤️ menggunakan Python, FastAPI, dan Biopython.*
