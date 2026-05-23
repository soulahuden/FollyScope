"""
NCBI Entrez integration for Folliscope.

Fetches the human Androgen Receptor (AR) reference mRNA — NM_000044.6 —
from NCBI RefSeq via Biopython Entrez. Used as the baseline against
which users' AR profiles are compared.

Reference: https://www.ncbi.nlm.nih.gov/nuccore/NM_000044.6
"""

import re
import time
from dataclasses import dataclass
from typing import Dict, Optional

from Bio import Entrez, SeqIO

# NCBI requires an email + tool name on every Entrez request.
Entrez.email = "folliscope.education@example.com"
Entrez.tool  = "Folliscope-EducationalProject"

# In-memory cache so we don't hit NCBI on every /api/analyze call.
_cache: Dict[str, tuple] = {}
CACHE_TTL = 3600  # 1 hour


@dataclass
class NCBIReferenceResult:
    accession:        str
    description:      str
    sequence_length:  int
    cag_count:        int
    cag_position:     Optional[tuple]   # (start, end) or None
    sequence_preview: str               # first 150 characters
    source:           str = "NCBI RefSeq"
    url:              str = "https://www.ncbi.nlm.nih.gov/nuccore/NM_000044.6"
    success:          bool = True
    error:            Optional[str] = None


def _cache_valid(key: str) -> bool:
    if key not in _cache:
        return False
    _, ts = _cache[key]
    return (time.time() - ts) < CACHE_TTL


def fetch_ar_reference() -> NCBIReferenceResult:
    """
    Fetch the AR reference mRNA sequence (NM_000044.6) from NCBI RefSeq.

    Serves three purposes:
      - Baseline CAG count for comparison against the user's profile
      - Bioinformatics context when users upload their own FASTA
      - Live evidence that the project integrates an authoritative database

    Cached for 1 hour to respect NCBI's 3-req/sec rate limit.
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
            error            = f"Could not contact NCBI: {str(exc)}",
        )
