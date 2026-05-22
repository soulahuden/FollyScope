# Folliscope — Tentang Proyek Ini

> Proyek edukasi mata kuliah Computational Biology — **bukan alat diagnostik klinis.**

---

## Apa Itu Folliscope?

Folliscope adalah *proof-of-concept* sistem peringatan dini berbasis web untuk memperkirakan risiko **Androgenetic Alopecia (AGA)** — kebotakan pola genetik yang mempengaruhi ~50% pria di atas usia 50 tahun dan 25–40% wanita sepanjang hidupnya.

Sistem ini menggabungkan dua jalur analisis:
- **Jalur Genetik** — analisis sekuens DNA (CAG/GGN repeat) dan panel 9 SNP
- **Jalur Klinis** — kuesioner 5 bagian meliputi gejala, riwayat keluarga, dan gaya hidup

Keduanya digabungkan dengan pendekatan *Hybrid Polygenic Risk Score (PRS)* untuk menghasilkan skor risiko 0–100.

---

## Metode yang Digunakan

### 1. Analisis Genetik

#### a. Penghitungan CAG Repeat

Gen **AR (Androgen Receptor)** di kromosom X mengandung pengulangan trinukleotida **(CAG)n** di exon 1. Jumlah repeat ini menentukan sensitivitas reseptor AR terhadap hormon DHT — semakin pendek, semakin sensitif, semakin tinggi risiko AGA.

Metode: pencarian pola regex `(?:CAG){5,}` pada sekuens FASTA yang diunggah, mengambil run terpanjang.

| Jumlah CAG | Kategori Risiko |
|------------|-----------------|
| < 18 | Sangat Tinggi |
| 18 – 21 | Tinggi |
| 22 – 24 | Sedang |
| 25 – 29 | Rendah |
| ≥ 30 | Protektif |

> **Status akurasi: ✅ Tervalidasi** — threshold ini berasal dari studi pada ratusan pasien (Choong et al. 1996; Hillmer et al. 2005). Arah efeknya (CAG pendek = risiko lebih tinggi) adalah konsensus ilmiah yang tidak terbantahkan.

#### b. Penghitungan GGN Repeat

Exon 1 AR juga mengandung **(GGN)n** yang mengkode poliglisina. Pola regex: `(?:GG[ATCGN]){5,}`.

| Jumlah GGN | Kategori Risiko |
|------------|-----------------|
| < 18 | Tinggi |
| 18 – 23 | Sedang |
| ≥ 24 | Rendah / Protektif |

> **Status akurasi: ✅ Tervalidasi** — berdasarkan Giovannucci et al. 1999. Namun efek GGN lebih lemah dan konsensusnya tidak sekuat CAG.

#### c. Analisis SNP Panel

9 SNP yang berkaitan dengan AGA dianalisis dari studi GWAS. Kontribusi tiap SNP:

```
kontribusi = bobot_PRS × (OddsRatio − 1)   [jika alel risiko ditemukan]
```

Total skor SNP dinormalisasi ke 0–100. Untuk data 23andMe, genotype diploid (`AG`, `GG`) ditangani dengan model dosage: `0.0` tidak ada risiko, `0.5` heterozygous, `1.0` homozygous risk.

> **Status akurasi: ✅ SNP dan OR-nya tervalidasi** dari GWAS ribuan sampel. ⚠️ **Namun** hanya 9 dari >200 lokus yang diketahui, dan nilai OR bisa berbeda antar populasi (studi sebagian besar pada populasi Kaukasian).

#### d. Formula GeneticScore

```
GeneticScore = 0.40 × CagScore + 0.15 × GgnScore + 0.45 × SNPScore
```

> **Status akurasi: ⚠️ Bobot belum tervalidasi** — proporsi 40/15/45 adalah keputusan desain yang belum dibuktikan dengan data pasien nyata.

---

### 2. Analisis Klinis (Kuesioner 5 Bagian)

#### a. ClinicalScore — Gejala Kerontokan

| Sub-komponen | Bobot | Metode Penilaian |
|---|---|---|
| Skala Norwood (pria) / Ludwig (wanita) | 35% | Norwood I→0, VII→100; Ludwig I→30, III→100 |
| Pola & area kerontokan | 20% | m-shape=70, vertex=65, diffuse=20 + bonus area |
| Hair Pull Test | 15% | ≤3=0, 4–6=20, 7–10=50, 11–20=75, >20=100 |
| Volume rontok per hari | 10% | ≤50=0, 51–100=15, ..., >250=100 |
| Miniaturisasi diameter | 10% | Ya=75, Tidak=0 |
| Durasi gejala | 10% | ≤1 bulan=10, ..., >24 bulan=95 |

> **Status akurasi: ✅ Skala Norwood dan Ludwig tervalidasi** secara klinis internasional (Norwood 1975; Ludwig 1977). ⚠️ **Namun** nilai numerik mapping (misalnya Norwood IV = 55) dan bobot antar sub-komponen adalah keputusan desain, bukan dari studi validasi.

#### b. FamilyScore — Riwayat Keluarga

| Anggota Keluarga | Bobot | Alasan |
|---|---|---|
| Kakek dari ibu | 35% | Pria mewarisi kromosom X dari ibu, ibu dari ayahnya |
| Ayah | 25% | Kontribusi autosomal dan interaksi |
| Kakek dari ayah | 15% | Pengaruh lebih lemah |
| Saudara laki-laki | 10% | Genetik bersama |
| Ibu (penipisan) | 8% | X-carrier |
| Jumlah generasi | 7% | Estimasi penetrance |

> **Status akurasi: ✅ Logika X-linked benar secara genetika** — bahwa kakek dari ibu lebih berpengaruh daripada kakek dari ayah adalah fakta biologis. ⚠️ **Namun** angka bobotnya (35%, 25%, dst) adalah perkiraan, bukan hasil regresi statistik dari data pasien.

#### c. LifestyleScore — Gaya Hidup

| Faktor | Bobot |
|--------|-------|
| Komorbiditas (PCOS, tiroid, anemia) | 25% |
| Tingkat stres | 25% |
| Merokok | 20% |
| Diet & olahraga | 15% |
| Jam tidur | 15% |

> **Status akurasi: ✅ Faktor-faktornya benar secara mekanisme biologis** — stres meningkatkan kortisol yang mempengaruhi androgen, merokok menyebabkan vasokonstriksi folikel, dll. ⚠️ **Namun** bobot 25%/20%/15% adalah keputusan desain tanpa validasi empiris.

#### d. Age Modifier

| Usia | Modifier |
|------|----------|
| < 25 tahun | × 1.15 |
| 25–29 tahun | × 1.08 |
| 30–39 tahun | × 1.00 |
| 40–49 tahun | × 0.95 |
| ≥ 50 tahun | × 0.90 |

> **Status akurasi: ✅ Arahnya benar** — onset dini memang menandakan komponen genetik lebih kuat. ⚠️ **Namun** nilai modifier spesifik (1.15, 1.08, dst) adalah perkiraan tanpa dasar empiris.

---

### 3. Formula Hybrid PRS

**Mode Hybrid** (data genetik tersedia):
```
HybridScore = (0.45 × GeneticScore
             + 0.30 × ClinicalScore
             + 0.15 × FamilyScore
             + 0.10 × LifestyleScore) × AgeModifier
```

**Mode Klinis Saja:**
```
ClinicalOnlyScore = (0.55 × ClinicalScore
                   + 0.30 × FamilyScore
                   + 0.15 × LifestyleScore) × AgeModifier
```

| Skor | Kategori |
|------|----------|
| 0–19 | Minimal |
| 20–39 | Rendah |
| 40–59 | Sedang |
| 60–79 | Tinggi |
| 80–100 | Sangat Tinggi |

> **Status akurasi: ⚠️ Bobot formula (0.45, 0.30, 0.15, 0.10) adalah bagian yang paling tidak tervalidasi** dalam seluruh sistem. Ini adalah keputusan desain berdasarkan pertimbangan ilmiah, bukan hasil dari regresi logistik atau machine learning terhadap data pasien nyata. PRS klinis yang sesungguhnya menggunakan koefisien yang diturunkan secara statistik dari ratusan ribu individu.

---

## Data yang Digunakan

### Sumber Data Referensi (dari Literatur)

Nilai-nilai berikut **bukan dari query database langsung**, melainkan diekstrak dari publikasi ilmiah dan dikodekan ke dalam sistem:

| Data | Sumber Literatur | Status |
|------|-----------------|--------|
| Threshold CAG repeat | Choong et al. 1996; Hillmer et al. 2005 | Tervalidasi |
| Threshold GGN repeat | Giovannucci et al. 1999 | Tervalidasi |
| 9 SNP dan nilai OR | Hillmer 2005; Heilmann-Heimbach 2017 | Tervalidasi |
| Skala Norwood | Norwood 1975 | Standar klinis |
| Skala Ludwig | Ludwig 1977 | Standar klinis |
| Bobot formula hybrid | Keputusan desain | **Belum tervalidasi** |

### Integrasi Database NCBI (Real-time)

Folliscope terhubung ke **NCBI RefSeq** secara langsung via Biopython Entrez:

```
Accession : NM_000044.6
Database  : NCBI Nucleotide (RefSeq)
Metode    : Biopython Entrez.efetch(db="nucleotide", id="NM_000044.6")
Tujuan    : Menyediakan sekuens AR referensi resmi sebagai pembanding
            saat pengguna mengupload sekuens mereka sendiri
```

Jumlah CAG pada sekuens referensi NCBI berfungsi sebagai baseline "normal" untuk konteks perbandingan.

### Input Data Pengguna

- **Sekuens FASTA** — exon 1 gen AR (opsional)
- **File genotype TSV** — alel 9 SNP (opsional)
- **File raw data 23andMe** — diekstrak otomatis 9 SNP yang relevan (opsional)
- **Kuesioner klinis** — 5 bagian (wajib)

### Data Sampel (Sintetis)

File di folder `sample_data/` adalah data **buatan** untuk keperluan demo, bukan data pasien nyata:

| File | Deskripsi |
|------|-----------|
| `high_risk_sample.fasta` | CAG=17, GGN=23 — simulasi profil risiko sangat tinggi |
| `medium_risk_sample.fasta` | CAG=23, GGN=22 — simulasi profil sedang |
| `low_risk_sample.fasta` | CAG=29, GGN=20 — simulasi profil rendah |
| `protective_sample.fasta` | CAG=33, GGN=18 — simulasi profil protektif |

---

## Seberapa Akurat Folliscope?

### Analogi yang Tepat

> Folliscope bekerja seperti **kompas**, bukan **GPS**.
> Kompas menunjukkan **arah yang benar** — faktor mana yang meningkatkan atau menurunkan risiko. Tapi kompas tidak bisa mengatakan *"kamu akan botak di usia 35 tahun"* dengan presisi angka.

### Apa yang Akurat

| Komponen | Mengapa Bisa Dipercaya |
|----------|----------------------|
| Mekanisme CAG → risiko | Konsensus ilmiah selama 30 tahun |
| Pilihan 9 SNP | Dari GWAS pada ribuan sampel |
| Nilai Odds Ratio | Dari publikasi peer-reviewed |
| Skala Norwood/Ludwig | Standar klinis internasional tervalidasi |
| Logika X-linked | Fakta biologis dasar genetika |
| Arah semua faktor risiko | Sesuai literatur dan mekanisme biologis |

### Apa yang Belum Tervalidasi

| Komponen | Mengapa Perlu Diakui |
|----------|---------------------|
| Bobot formula (0.45, 0.30, dst) | Tidak berasal dari regresi statistik data pasien |
| Nilai age modifier | Perkiraan, bukan dari studi empiris |
| Normalisasi skor 0–100 | Skala buatan tanpa distribusi populasi |
| Cut-off kategori (0–19, 20–39, dst) | Tidak ada studi yang memvalidasi angka batas ini |
| Performa prediktif keseluruhan | Belum diuji pada kohort pasien AGA yang terdiagnosis |

### Cara PRS Klinis yang Sesungguhnya

Sebagai konteks, PRS yang digunakan secara klinis dibangun dengan:
1. Data ratusan ribu individu (sebagian AGA, sebagian tidak)
2. GWAS untuk identifikasi ratusan lokus signifikan
3. Regresi logistik untuk menentukan bobot setiap varian
4. Validasi di cohort independen (AUC, sensitivity, specificity)
5. Kalibrasi berdasarkan populasi spesifik

Folliscope melewati langkah 1–4 dan langsung menggunakan nilai dari literatur dengan bobot yang dirancang secara manual — yang merupakan penyederhanaan yang **wajar untuk proyek edukasi**, namun perlu diakui secara terbuka.

---

## Kesimpulan Akademik

Folliscope adalah implementasi *proof-of-concept* yang:

- ✅ Mengimplementasikan faktor-faktor risiko AGA yang terbukti secara ilmiah
- ✅ Menggunakan nilai referensi dari literatur peer-reviewed
- ✅ Terhubung ke database NCBI untuk sekuens referensi gen AR
- ✅ Mendukung input data genetik nyata (FASTA, TSV, 23andMe)
- ⚠️ Menggunakan bobot formula yang belum divalidasi secara klinis
- ❌ Tidak memiliki dataset pasien nyata untuk validasi prediksi

**Yang bisa diklaim:** *Sistem ini mengimplementasikan komponen-komponen yang secara ilmiah terbukti relevan dengan AGA dalam sebuah arsitektur hybrid. Arah dan jenis faktor risiko yang digunakan berbasis literatur yang kuat. Namun, formula penggabungannya belum divalidasi secara empiris dan hasilnya bersifat indikatif, bukan prediktif secara klinis.*

---

## Referensi Literatur

1. Hillmer AM, et al. (2005). Genetic variation in the human androgen receptor gene is the major determinant of common early-onset androgenetic alopecia. *Am J Hum Genet*, 77(1):140–148.
2. Heilmann-Heimbach S, et al. (2017). Meta-analysis identifies novel risk loci and yields systematic insights into the biology of male-pattern baldness. *Nat Commun*, 8:14694.
3. Choong CS, et al. (1996). Reduced androgen receptor gene expression with first exon CAG repeat expansion. *Mol Endocrinol*, 10(12):1527–1535.
4. Giovannucci E, et al. (1997). The CAG repeat within the androgen receptor gene and its relationship to prostate cancer. *Proc Natl Acad Sci USA*, 94(7):3320–3323.
5. Norwood OT. (1975). Male pattern baldness: Classification and incidence. *South Med J*, 68(11):1359–1365.
6. Ludwig E. (1977). Classification of the types of androgenetic alopecia occurring in the female sex. *Br J Dermatol*, 97(3):247–254.
7. Ellis JA, et al. (2001). Polymorphism of the androgen receptor gene is associated with male pattern baldness. *J Invest Dermatol*, 116(3):452–455.
8. Prodi DA, et al. (2008). EDA2R is associated with androgenetic alopecia. *J Invest Dermatol*, 128(9):2268–2270.
