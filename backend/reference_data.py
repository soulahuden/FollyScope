"""Reference data for Folliscope — SNP database, CAG thresholds, and recommendations."""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

@dataclass
class SNPRecord:
    rs_id: str
    gene: str
    chromosome: str
    risk_allele: str
    ref_allele: str
    odds_ratio: float
    prs_weight: float
    description: str
    function: str

SNP_DATABASE: List[SNPRecord] = [
    SNPRecord("rs6152", "AR", "X", "G", "A", 2.50, 0.9, "Androgen Receptor exon 1 variant", "Meningkatkan sensitivitas reseptor androgen terhadap DHT"),
    SNPRecord("rs1385699", "EDA2R", "X", "C", "T", 2.20, 0.85, "Ectodysplasin A2 receptor variant", "Mengatur sinyal folikel rambut via EDA pathway"),
    SNPRecord("rs12558842", "AR", "X", "G", "A", 1.80, 0.70, "AR regulatory region variant", "Mempengaruhi ekspresi gen AR di folikel rambut"),
    SNPRecord("rs2497938", "AR", "X", "C", "T", 1.75, 0.65, "AR intronic variant", "Modulator transkripsi AR"),
    SNPRecord("rs7349332", "WNT10A", "2", "T", "C", 1.45, 0.50, "WNT signaling pathway variant", "Mengatur siklus folikel rambut via Wnt/β-catenin"),
    SNPRecord("rs9479482", "HDAC9", "7", "C", "T", 1.35, 0.45, "Histone deacetylase 9 variant", "Epigenetik regulasi ekspresi gen folikel"),
    SNPRecord("rs1160312", "PAX1", "20", "A", "G", 1.60, 0.60, "PAX1/FOXA2 locus variant", "Transkripsi faktor pengatur diferensiasi folikel"),
    SNPRecord("rs929626", "EBF1", "5", "C", "G", 1.30, 0.35, "Early B-cell factor 1 variant", "Regulasi siklus pertumbuhan rambut"),
    SNPRecord("rs523349", "SRD5A2", "2", "G", "C", 1.40, 0.55, "5-alpha reductase type 2 variant", "Enzim konversi testosteron → DHT di folikel rambut"),
]

# CAG repeat thresholds (Choong 1996, Hillmer 2005)
CAG_THRESHOLDS = [
    (0, 17, "SANGAT_TINGGI", 100, "CAG sangat pendek: reseptor AR sangat sensitif DHT"),
    (18, 21, "TINGGI", 80, "CAG pendek: sensitivitas AR tinggi"),
    (22, 24, "SEDANG", 60, "CAG moderat: sensitivitas AR sedang"),
    (25, 29, "RENDAH", 30, "CAG normal-panjang: sensitivitas AR rendah"),
    (30, 999, "PROTEKTIF", 10, "CAG panjang: efek protektif terhadap AGA"),
]

# GGN repeat thresholds
GGN_THRESHOLDS = [
    (0, 17, "TINGGI", 75, "GGN pendek"),
    (18, 23, "SEDANG", 50, "GGN moderat"),
    (24, 999, "RENDAH", 20, "GGN panjang: efek protektif"),
]

# Risk categories
RISK_CATEGORIES = {
    (0, 19): ("MINIMAL", "#2ecc71", "Risiko minimal terdeteksi"),
    (20, 39): ("RENDAH", "#27ae60", "Risiko rendah terdeteksi"),
    (40, 59): ("SEDANG", "#f39c12", "Risiko sedang terdeteksi"),
    (60, 79): ("TINGGI", "#e67e22", "Risiko tinggi terdeteksi"),
    (80, 100): ("SANGAT_TINGGI", "#e74c3c", "Risiko sangat tinggi terdeteksi"),
}

RECOMMENDATIONS = {
    "MINIMAL": [
        "Tidak ada tindakan khusus yang diperlukan saat ini.",
        "Pertahankan pola hidup sehat: tidur cukup, diet seimbang, olahraga teratur.",
        "Monitor kondisi rambut secara berkala.",
        "Disarankan re-evaluasi setiap 5 tahun atau jika ada keluhan baru.",
    ],
    "RENDAH": [
        "Perhatikan pola kerontokan rambut (normal: 50-100 helai/hari).",
        "Konsumsi makanan kaya biotin, zinc, protein, dan besi.",
        "Jaga kesehatan kulit kepala dengan sampo yang sesuai.",
        "Kurangi stres dan pastikan tidur 7-8 jam/hari.",
        "Pertimbangkan konsultasi dermatologi jika ada perubahan signifikan.",
    ],
    "SEDANG": [
        "⚠️ PERINGATAN DINI: Kerentanan moderat terhadap AGA terdeteksi.",
        "Disarankan pemeriksaan trichoscopy dan kadar DHT serum.",
        "Pertimbangkan penggunaan sampo anti-DHT (ketoconazole 2%, saw palmetto).",
        "Suplemen: biotin 5000mcg, zinc, vitamin D, omega-3.",
        "Konsultasi dermatologis jika ada penipisan yang terlihat.",
        "Hindari styling agresif, bleaching, dan kuncir ketat.",
        "Re-evaluasi setiap 12 bulan.",
    ],
    "TINGGI": [
        "🚨 PERINGATAN: Risiko AGA tinggi — intervensi dini sangat dianjurkan.",
        "Segera konsultasi DERMATOLOG dalam 1-3 bulan.",
        "Pertimbangkan minoxidil topikal 5% (tersedia tanpa resep).",
        "Diskusikan finasteride 1mg/hari dengan dokter spesialis.",
        "Periksa laboratorium: kadar DHT, ferritin, vitamin D, fungsi tiroid.",
        "Foto dokumentasi keadaan rambut sekarang sebagai baseline.",
        "Evaluasi faktor-faktor yang dapat dimodifikasi (stres, tidur, nutrisi).",
        "Re-evaluasi setiap 6 bulan dengan dermatolog.",
    ],
    "SANGAT_TINGGI": [
        "🔴 WASPADA: Risiko genetik sangat tinggi — tindakan segera diperlukan.",
        "Konsultasi DERMATOLOG SEGERA (dalam 1 bulan).",
        "Pertimbangkan terapi kombinasi: minoxidil + finasteride atau dutasteride.",
        "Diskusikan terapi lanjutan: PRP (Platelet Rich Plasma), LLLT (Laser Therapy).",
        "Pemeriksaan komprehensif: DHT, testosterone, SHBG, ferritin, vitamin D, tiroid.",
        "Skrining penyakit terkait: sindrom metabolik, penyakit jantung koroner.",
        "Untuk wanita: skrining PCOS, evaluasi kadar androgen.",
        "Dokumentasi progresivitas dengan foto serial setiap 3 bulan.",
        "Pertimbangkan konseling genetik jika berencana punya anak.",
    ],
}
