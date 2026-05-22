"""
Parser untuk file raw data 23andMe.

Format file 23andMe (tab-separated):
    # komentar diawali '#'
    rsid        chromosome  position    genotype
    rs6152      X           66763947    AG
    rs523349    2           31806283    GG
    ...

Genotype bersifat diploid (dua karakter), misalnya:
    "GG" = homozygous risk
    "AG" = heterozygous (carrier)
    "AA" = homozygous reference (non-risk)
    "--" = no call (tidak terbaca)

Parser ini hanya mengekstrak 9 SNP yang relevan dengan AGA dari panel
Folliscope, lalu mengkonversinya ke format yang kompatibel dengan
analyze_snps() yang sudah ada.
"""

from dataclasses import dataclass
from typing import Dict, Optional

from .reference_data import SNP_DATABASE

# Lookup cepat berdasarkan rs_id
_PANEL    = {snp.rs_id for snp in SNP_DATABASE}
_RISK_MAP = {snp.rs_id: snp.risk_allele for snp in SNP_DATABASE}
_REF_MAP  = {snp.rs_id: snp.ref_allele  for snp in SNP_DATABASE}


@dataclass
class ParsedSNP:
    rs_id:           str
    chromosome:      str
    genotype:        str    # raw diploid, misal "AG"
    allele1:         str
    allele2:         str
    is_heterozygous: bool
    is_no_call:      bool
    risk_allele:     str
    ref_allele:      str
    risk_dosage:     float  # 0.0 = no risk | 0.5 = het | 1.0 = hom risk


@dataclass
class Parse23andMeResult:
    snp_genotypes:  Dict[str, str]        # rs_id → alel (langsung ke analyze_snps)
    parsed_snps:    Dict[str, ParsedSNP]  # detail per SNP untuk ditampilkan ke user
    found_count:    int   # SNP yang ditemukan di file
    callable_count: int   # SNP yang bisa dibaca (bukan "--")
    no_call_count:  int   # SNP dengan "--"
    missing_count:  int   # SNP panel yang tidak ada di file
    total_in_panel: int   # selalu 9


def parse_23andme(text: str) -> Parse23andMeResult:
    """
    Parse file raw data 23andMe dan ekstrak 9 SNP AGA panel Folliscope.

    Penanganan heterozygous:
    - Jika salah satu alel adalah risk allele → dilaporkan sebagai risk
      (conservative: sedikit overestimate untuk heterozygous carrier)
    - risk_dosage: 0.0 / 0.5 / 1.0 untuk keperluan tampilan
    """
    parsed: Dict[str, ParsedSNP] = {}

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split("\t")
        if len(parts) < 4:
            continue

        rs_id = parts[0].strip()
        if rs_id not in _PANEL:
            continue  # bukan salah satu dari 9 SNP yang kita butuhkan

        chromosome = parts[1].strip()
        genotype   = parts[3].strip().upper()
        risk       = _RISK_MAP[rs_id]
        ref        = _REF_MAP[rs_id]

        # No-call
        if genotype in ("--", ""):
            parsed[rs_id] = ParsedSNP(
                rs_id=rs_id, chromosome=chromosome, genotype=genotype,
                allele1="", allele2="",
                is_heterozygous=False, is_no_call=True,
                risk_allele=risk, ref_allele=ref, risk_dosage=0.0,
            )
            continue

        a1 = genotype[0] if len(genotype) >= 1 else ""
        a2 = genotype[1] if len(genotype) >= 2 else a1
        risk_count = [a1, a2].count(risk)
        dosage     = risk_count / 2.0

        parsed[rs_id] = ParsedSNP(
            rs_id=rs_id, chromosome=chromosome, genotype=genotype,
            allele1=a1, allele2=a2,
            is_heterozygous=(a1 != a2), is_no_call=False,
            risk_allele=risk, ref_allele=ref, risk_dosage=dosage,
        )

    # Konversi ke format analyze_snps(): Dict[rs_id, single_allele]
    # Jika ada alel risiko (termasuk heterozygous) → kirim risk allele
    snp_genotypes: Dict[str, str] = {}
    for rs_id, snp in parsed.items():
        if snp.is_no_call:
            continue
        snp_genotypes[rs_id] = snp.risk_allele if snp.risk_dosage > 0 else snp.ref_allele

    total   = len(SNP_DATABASE)
    found   = len(parsed)
    no_call = sum(1 for s in parsed.values() if s.is_no_call)

    return Parse23andMeResult(
        snp_genotypes  = snp_genotypes,
        parsed_snps    = parsed,
        found_count    = found,
        callable_count = found - no_call,
        no_call_count  = no_call,
        missing_count  = total - found,
        total_in_panel = total,
    )
