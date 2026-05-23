"""
Genetic analyzer for Folliscope.
Counts CAG/GGN repeats and detects SNPs in AR gene sequences.
Ref: Choong 1996, Hillmer 2005 (Am J Hum Genet)
"""

import re
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple

from .reference_data import SNP_DATABASE, CAG_THRESHOLDS, GGN_THRESHOLDS


@dataclass
class RepeatResult:
    repeat_type: str
    count: int
    raw_matches: List[str]
    sequence_position: Optional[Tuple[int, int]]
    risk_level: str
    risk_score: float
    interpretation: str


@dataclass
class SNPResult:
    rs_id: str
    gene: str
    user_allele: Optional[str]
    risk_allele: str
    ref_allele: str
    is_risk: bool
    odds_ratio: float
    prs_weight: float
    contribution: float
    status: str  # "RISK" | "NORMAL" | "UNKNOWN"


@dataclass
class GeneticAnalysisResult:
    cag_result: RepeatResult
    ggn_result: RepeatResult
    snp_results: List[SNPResult]
    raw_sequence: str
    sequence_length: int
    genetic_score: float  # 0-100
    has_snp_data: bool
    has_sequence_data: bool


def parse_fasta(fasta_text: str) -> str:
    """Parse FASTA format text and return the clean sequence."""
    lines = fasta_text.strip().split('\n')
    seq_lines = [l.strip() for l in lines if l.strip() and not l.startswith('>')]
    sequence = ''.join(seq_lines).upper()
    # Keep only valid nucleotide characters
    sequence = re.sub(r'[^ATCGN]', '', sequence)
    return sequence


def count_cag_repeats(sequence: str) -> RepeatResult:
    """
    Count CAG trinucleotide repeats in AR exon 1.
    Pattern: (CAG){5,}, minimum 5 consecutive repeats.
    Ref: Choong et al. 1996, Hillmer et al. 2005
    """
    pattern = r'(?:CAG){5,}'
    matches = list(re.finditer(pattern, sequence))

    if not matches:
        # Try to find shorter runs and estimate
        short_pattern = r'(?:CAG){2,}'
        short_matches = list(re.finditer(short_pattern, sequence))
        if short_matches:
            longest = max(short_matches, key=lambda m: len(m.group()))
            count = len(longest.group()) // 3
        else:
            count = 0
        position = None
        raw_matches = []
    else:
        # Take the longest match (actual CAG tract)
        longest_match = max(matches, key=lambda m: len(m.group()))
        count = len(longest_match.group()) // 3
        position = (longest_match.start(), longest_match.end())
        raw_matches = [m.group() for m in matches]

    # Determine risk level based on CAG thresholds
    risk_level, risk_score, interpretation = _get_cag_risk(count)

    return RepeatResult(
        repeat_type="CAG",
        count=count,
        raw_matches=raw_matches,
        sequence_position=position,
        risk_level=risk_level,
        risk_score=risk_score,
        interpretation=interpretation
    )


def count_ggn_repeats(sequence: str) -> RepeatResult:
    """
    Count GGN trinucleotide repeats in AR exon 1 (polyglycine tract).
    Pattern: (GG[ATCG]){5,}
    Ref: Giovannucci et al. 1999
    """
    pattern = r'(?:GG[ATCGN]){5,}'
    matches = list(re.finditer(pattern, sequence))

    if not matches:
        short_pattern = r'(?:GG[ATCGN]){2,}'
        short_matches = list(re.finditer(short_pattern, sequence))
        if short_matches:
            longest = max(short_matches, key=lambda m: len(m.group()))
            count = len(longest.group()) // 3
        else:
            count = 0
        position = None
        raw_matches = []
    else:
        longest_match = max(matches, key=lambda m: len(m.group()))
        count = len(longest_match.group()) // 3
        position = (longest_match.start(), longest_match.end())
        raw_matches = [m.group() for m in matches]

    risk_level, risk_score, interpretation = _get_ggn_risk(count)

    return RepeatResult(
        repeat_type="GGN",
        count=count,
        raw_matches=raw_matches,
        sequence_position=position,
        risk_level=risk_level,
        risk_score=risk_score,
        interpretation=interpretation
    )


def _get_cag_risk(count: int) -> Tuple[str, float, str]:
    """Map CAG repeat count to risk level and score."""
    for low, high, level, score, interp in CAG_THRESHOLDS:
        if low <= count <= high:
            return level, float(score), interp
    return "TIDAK_DIKETAHUI", 50.0, "Repeat count outside reference range"


def _get_ggn_risk(count: int) -> Tuple[str, float, str]:
    """Map GGN repeat count to risk level and score."""
    for low, high, level, score, interp in GGN_THRESHOLDS:
        if low <= count <= high:
            return level, float(score), interp
    return "TIDAK_DIKETAHUI", 40.0, "Repeat count outside reference range"


def analyze_snps(snp_genotypes: Dict[str, str]) -> List[SNPResult]:
    """
    Analyze user SNP genotypes against risk allele database.
    Input: dict of {rs_id: allele} e.g. {"rs6152": "G"}
    """
    results = []
    for snp_record in SNP_DATABASE:
        user_allele = snp_genotypes.get(snp_record.rs_id)

        if user_allele is None:
            results.append(SNPResult(
                rs_id=snp_record.rs_id,
                gene=snp_record.gene,
                user_allele=None,
                risk_allele=snp_record.risk_allele,
                ref_allele=snp_record.ref_allele,
                is_risk=False,
                odds_ratio=snp_record.odds_ratio,
                prs_weight=snp_record.prs_weight,
                contribution=0.0,
                status="UNKNOWN"
            ))
        else:
            user_allele = user_allele.strip().upper()
            is_risk = (user_allele == snp_record.risk_allele)
            # Contribution: weight * normalized OR if risk allele present
            contribution = snp_record.prs_weight * (snp_record.odds_ratio - 1.0) if is_risk else 0.0
            results.append(SNPResult(
                rs_id=snp_record.rs_id,
                gene=snp_record.gene,
                user_allele=user_allele,
                risk_allele=snp_record.risk_allele,
                ref_allele=snp_record.ref_allele,
                is_risk=is_risk,
                odds_ratio=snp_record.odds_ratio,
                prs_weight=snp_record.prs_weight,
                contribution=contribution,
                status="RISK" if is_risk else "NORMAL"
            ))
    return results


def calculate_snp_score(snp_results: List[SNPResult]) -> float:
    """
    Calculate normalized SNP risk score 0-100 from PRS contributions.
    Max possible contribution = sum of all weights * (max_OR - 1)
    """
    if not snp_results:
        return 0.0

    known_results = [r for r in snp_results if r.status != "UNKNOWN"]
    if not known_results:
        return 0.0

    total_contribution = sum(r.contribution for r in known_results)
    max_contribution = sum(r.prs_weight * (r.odds_ratio - 1.0) for r in known_results)

    if max_contribution == 0:
        return 0.0

    score = (total_contribution / max_contribution) * 100.0
    return min(max(score, 0.0), 100.0)


def calculate_genetic_score(cag_result: RepeatResult, ggn_result: RepeatResult, snp_results: List[SNPResult]) -> float:
    """
    Calculate overall genetic score 0-100.
    Weights: CAG 40%, GGN 15%, SNP panel 45%
    """
    cag_score = cag_result.risk_score if cag_result.count > 0 else 50.0
    ggn_score = ggn_result.risk_score if ggn_result.count > 0 else 40.0
    snp_score = calculate_snp_score(snp_results)

    has_snp = any(r.status != "UNKNOWN" for r in snp_results)

    if has_snp and (cag_result.count > 0 or ggn_result.count > 0):
        # Full genetic data
        genetic_score = 0.40 * cag_score + 0.15 * ggn_score + 0.45 * snp_score
    elif cag_result.count > 0 or ggn_result.count > 0:
        # Only sequence data
        genetic_score = 0.73 * cag_score + 0.27 * ggn_score
    elif has_snp:
        # Only SNP data
        genetic_score = snp_score
    else:
        return 0.0

    return min(max(genetic_score, 0.0), 100.0)


def parse_tsv_genotypes(tsv_text: str) -> Dict[str, str]:
    """
    Parse TSV format genotype file.
    Expected format: rs_id\tallele (one per line)
    """
    genotypes = {}
    for line in tsv_text.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) >= 2:
            rs_id = parts[0].strip()
            allele = parts[1].strip().upper()
            if rs_id.startswith('rs'):
                genotypes[rs_id] = allele
    return genotypes


def run_genetic_analysis(
    fasta_text: Optional[str] = None,
    snp_genotypes: Optional[Dict[str, str]] = None
) -> GeneticAnalysisResult:
    """Main genetic analysis pipeline."""
    has_sequence = bool(fasta_text and fasta_text.strip())
    has_snp = bool(snp_genotypes)

    if has_sequence:
        sequence = parse_fasta(fasta_text)
    else:
        sequence = ""

    cag_result = count_cag_repeats(sequence) if has_sequence else RepeatResult(
        "CAG", 0, [], None, "TIDAK_DIKETAHUI", 50.0, "No sequence data provided"
    )
    ggn_result = count_ggn_repeats(sequence) if has_sequence else RepeatResult(
        "GGN", 0, [], None, "TIDAK_DIKETAHUI", 40.0, "No sequence data provided"
    )

    snp_results = analyze_snps(snp_genotypes or {})
    genetic_score = calculate_genetic_score(cag_result, ggn_result, snp_results)

    return GeneticAnalysisResult(
        cag_result=cag_result,
        ggn_result=ggn_result,
        snp_results=snp_results,
        raw_sequence=sequence[:200] + "..." if len(sequence) > 200 else sequence,
        sequence_length=len(sequence),
        genetic_score=genetic_score,
        has_snp_data=has_snp,
        has_sequence_data=has_sequence
    )
