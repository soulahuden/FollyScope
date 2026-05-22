"""
NCBI Entrez integration for Folliscope.
Fetches AR gene reference sequence (NM_000044.6) from NCBI RefSeq
using Biopython Entrez — memenuhi syarat penggunaan database NCBI.

Referensi: https://www.ncbi.nlm.nih.gov/nuccore/NM_000044.6
"""

import re
import time
from dataclasses import dataclass
from typing import Dict, Optional

from Bio import Entrez, SeqIO

# NCBI mewajibkan email untuk setiap query Entrez
Entrez.email = "folliscope.education@example.com"
Entrez.tool  = "Folliscope-EducationalProject"

# Cache in-memory: simpan hasil agar tidak query NCBI berulang kali
_cache: Dict[str, tuple] = {}
CACHE_TTL = 3600  # 1 jam


@dataclass
class NCBIReferenceResult:
    accession:        str
    description:      str
    sequence_length:  int
    cag_count:        int
    cag_position:     Optional[tuple]   # (start, end) atau None
    sequence_preview: str               # 150 karakter pertama
    source:           str = "NCBI RefSeq"
    success:          bool = True
    error:            Optional[str] = None


def _cache_valid(key: str) -> bool:
    if key not in _cache:
        return False
    _, ts = _cache[key]
    return (time.time() - ts) < CACHE_TTL


def fetch_ar_reference() -> NCBIReferenceResult:
    """
    Ambil sekuens mRNA Androgen Receptor dari NCBI RefSeq.
    Accession: NM_000044.6 (Homo sapiens androgen receptor, transcript variant 1)

    Digunakan sebagai:
    - Referensi jumlah CAG repeat pada individu normal
    - Konteks bioinformatika saat pengguna upload FASTA mereka sendiri
    - Bukti integrasi database NCBI dalam proyek ini

    Hasil di-cache selama 1 jam untuk menghindari rate-limit NCBI (3 req/detik).
    """
    key = "AR_NM_000044_6"

    if _cache_valid(key):
        return _cache[key][0]

    try:
        handle = Entrez.efetch(
            db="nucleotide",
            id="NM_000044.6",
            rettype="fasta",
            retmode="text",
        )
        record = SeqIO.read(handle, "fasta")
        handle.close()

        sequence = re.sub(r"[^ATCGN]", "", str(record.seq).upper())

        # Temukan CAG repeat terpanjang di sekuens referensi
        matches = list(re.finditer(r"(?:CAG){5,}", sequence))
        if matches:
            longest     = max(matches, key=lambda m: len(m.group()))
            cag_count   = len(longest.group()) // 3
            cag_position = (longest.start(), longest.end())
        else:
            cag_count    = 0
            cag_position = None

        result = NCBIReferenceResult(
            accession        = "NM_000044.6",
            description      = record.description[:200],
            sequence_length  = len(sequence),
            cag_count        = cag_count,
            cag_position     = cag_position,
            sequence_preview = sequence[:150] + "...",
        )

        _cache[key] = (result, time.time())
        return result

    except Exception as exc:
        return NCBIReferenceResult(
            accession        = "NM_000044.6",
            description      = "",
            sequence_length  = 0,
            cag_count        = 0,
            cag_position     = None,
            sequence_preview = "",
            success          = False,
            error            = f"Gagal menghubungi NCBI: {str(exc)}",
        )
