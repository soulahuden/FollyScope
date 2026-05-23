"""
Phenotype-to-genotype inference for Folliscope.

Estimates a probable AR CAG-repeat range and overall genetic-risk
profile from the clinical questionnaire ALONE, used when the user has
no DNA data. Compared side-by-side against the NCBI AR reference
(NM_000044.6, ~22 CAG) so general users still get an interpretable,
education-friendly genetic narrative.

This is *inference*, not measurement. Confidence is reported
transparently so users understand the limits of the estimate.
"""

from dataclasses import dataclass
from typing import List, Optional

from .clinical_analyzer import ClinicalAnalysisResult, Section1Data
from .analyzer import GeneticAnalysisResult

# NCBI AR reference CAG count (NM_000044.6) is ~22 in the consensus
# transcript. We use 22 as the educational baseline for "normal".
NCBI_REFERENCE_CAG = 22


@dataclass
class PhenotypeInference:
    """Probable genetic profile inferred from clinical data."""
    estimated_cag_min: int
    estimated_cag_max: int
    estimated_cag_midpoint: int
    estimated_risk_band: str          # PROTECTIVE | LOW | MODERATE | HIGH | VERY_HIGH
    inference_confidence: str         # low | medium | high
    reasoning: List[str]              # Plain-English reasons feeding the estimate
    reference_cag: int = NCBI_REFERENCE_CAG
    delta_vs_reference: int = 0       # midpoint - reference (negative = shorter = more sensitive)


def _norwood_ludwig_severity(clinical: ClinicalAnalysisResult) -> float:
    """Return Norwood/Ludwig severity as 0.0-1.0."""
    score = clinical.clinical_breakdown.norwood_ludwig_score
    return min(max(score / 100.0, 0.0), 1.0)


def _family_pressure(clinical: ClinicalAnalysisResult) -> float:
    """X-linked weighted family-history pressure as 0.0-1.0."""
    fb = clinical.family_breakdown
    # Maternal grandfather is heaviest signal because AR is X-linked.
    score = (
        0.50 * fb.maternal_grandfather_score
        + 0.30 * fb.father_score
        + 0.10 * fb.paternal_grandfather_score
        + 0.10 * fb.brothers_score
    )
    return min(max(score / 100.0, 0.0), 1.0)


def _early_onset_signal(s1: Section1Data, clinical: ClinicalAnalysisResult) -> float:
    """Early onset (young age + visible symptoms) is a strong AR signal. 0.0-1.0."""
    if s1.age >= 35:
        return 0.0
    symptom_load = clinical.clinical_breakdown.total_clinical_score / 100.0
    age_weight = (35 - s1.age) / 20.0  # full weight at 15, none at 35
    return min(age_weight * symptom_load, 1.0)


def infer_phenotype_profile(
    s1: Section1Data,
    clinical: ClinicalAnalysisResult,
) -> PhenotypeInference:
    """
    Estimate a probable AR CAG-repeat range from clinical signals.

    Method (transparent, rule-based, defensible for an educational tool):
      - Start from the NCBI baseline of 22 CAG.
      - Subtract repeats as symptom severity + family pressure + early-onset
        signal accumulate (shorter CAG = higher AR sensitivity).
      - Confidence depends on how much corroborating evidence we have.
    """
    severity = _norwood_ludwig_severity(clinical)
    family   = _family_pressure(clinical)
    early    = _early_onset_signal(s1, clinical)

    # Total "shift down" from reference, weighted across signals.
    # Max shift is ~9 CAG (22 - 13) under maximal evidence; capped at 13 floor.
    shift = (4.0 * severity) + (3.5 * family) + (2.5 * early)
    shift = min(shift, 9.5)

    midpoint = max(int(round(NCBI_REFERENCE_CAG - shift)), 12)
    spread   = 2 if (severity + family + early) > 1.2 else 3
    cag_min  = max(midpoint - spread, 10)
    cag_max  = min(midpoint + spread, 40)

    # Risk band from midpoint (mirrors CAG_THRESHOLDS in reference_data).
    if midpoint < 18:
        band = "VERY_HIGH"
    elif midpoint <= 21:
        band = "HIGH"
    elif midpoint <= 24:
        band = "MODERATE"
    elif midpoint <= 29:
        band = "LOW"
    else:
        band = "PROTECTIVE"

    # Confidence: more signals + stronger evidence = higher confidence.
    signal_count = sum(x > 0.25 for x in (severity, family, early))
    if signal_count >= 2 and (severity > 0.5 or family > 0.5):
        confidence = "medium"
    elif signal_count >= 1:
        confidence = "low"
    else:
        confidence = "low"

    reasoning = _build_reasoning(severity, family, early, s1.age)

    return PhenotypeInference(
        estimated_cag_min      = cag_min,
        estimated_cag_max      = cag_max,
        estimated_cag_midpoint = midpoint,
        estimated_risk_band    = band,
        inference_confidence   = confidence,
        reasoning              = reasoning,
        delta_vs_reference     = midpoint - NCBI_REFERENCE_CAG,
    )


def _build_reasoning(severity: float, family: float, early: float, age: int) -> List[str]:
    """Plain-English reasons fed into the estimate, for transparency."""
    reasons: List[str] = []
    if severity >= 0.6:
        reasons.append("Advanced hair-loss pattern (Norwood IV+ or Ludwig II+) suggests strong AR-driven follicle miniaturization.")
    elif severity >= 0.25:
        reasons.append("Mild-to-moderate visible thinning indicates some AR pathway activity.")

    if family >= 0.5:
        reasons.append("Strong family history (especially maternal grandfather) is the dominant X-linked signal for shorter CAG.")
    elif family >= 0.2:
        reasons.append("Some family history of androgenetic alopecia raises the probability of inherited AR sensitivity.")

    if early >= 0.35:
        reasons.append("Early-onset symptoms (under age 35 with visible loss) typically associate with shorter CAG tracts.")

    if not reasons:
        reasons.append("Limited symptoms and family signal, the estimate stays close to the population baseline.")

    return reasons


# ─── Confidence level for the OVERALL analysis ─────────────────────────────────

@dataclass
class AnalysisConfidence:
    level: str            # questionnaire_only | questionnaire_plus_snp | questionnaire_plus_dna
    label: str            # Human-friendly label
    percent: int          # Rough confidence percentage for UI
    description: str
    inputs_used: List[str]


def compute_confidence(
    genetic: Optional[GeneticAnalysisResult],
) -> AnalysisConfidence:
    """Return a transparent confidence indicator based on available inputs."""
    has_sequence = bool(genetic and genetic.has_sequence_data)
    has_snp      = bool(genetic and genetic.has_snp_data)

    if has_sequence:
        return AnalysisConfidence(
            level       = "questionnaire_plus_dna",
            label       = "Questionnaire + DNA sequence",
            percent     = 95,
            description = "Direct measurement of your AR CAG repeats from DNA sequence gives the highest confidence.",
            inputs_used = ["Clinical questionnaire", "DNA sequence (FASTA)", "NCBI reference"]
            + (["SNP panel"] if has_snp else []),
        )
    if has_snp:
        return AnalysisConfidence(
            level       = "questionnaire_plus_snp",
            label       = "Questionnaire + SNP panel",
            percent     = 85,
            description = "Your SNP genotypes add measured genetic signal alongside the clinical inference.",
            inputs_used = ["Clinical questionnaire", "SNP panel", "NCBI reference"],
        )
    return AnalysisConfidence(
        level       = "questionnaire_only",
        label       = "Questionnaire only",
        percent     = 70,
        description = "Your genetic profile is inferred from clinical signals and compared against the NCBI reference. Upload DNA or SNP data for higher confidence.",
        inputs_used = ["Clinical questionnaire", "NCBI reference (educational baseline)"],
    )


# ─── Build a user-facing comparison block ──────────────────────────────────────

def build_ncbi_comparison(
    inference: PhenotypeInference,
    genetic: Optional[GeneticAnalysisResult],
    ncbi_ref_cag: int,
    ncbi_accession: str,
    ncbi_available: bool,
) -> dict:
    """
    Build the side-by-side comparison block consumed by the frontend.

    Always shows:
      - NCBI reference CAG (educational baseline)
      - User CAG: measured (if DNA provided) or estimated range (otherwise)
      - Plain-English interpretation of the difference
    """
    measured = bool(genetic and genetic.has_sequence_data and genetic.cag_result.count > 0)
    measured_cag = genetic.cag_result.count if measured else None

    user_value_min = measured_cag if measured else inference.estimated_cag_min
    user_value_max = measured_cag if measured else inference.estimated_cag_max
    user_midpoint  = measured_cag if measured else inference.estimated_cag_midpoint

    delta = user_midpoint - ncbi_ref_cag

    if delta <= -5:
        interpretation = (
            f"Your AR profile sits well below the NCBI reference ({ncbi_ref_cag} CAG). "
            "Shorter CAG repeats make the androgen receptor more responsive to DHT, "
            "which is associated with higher AGA susceptibility."
        )
        comparison_band = "shorter_significant"
    elif delta <= -2:
        interpretation = (
            f"Your AR profile is moderately shorter than the NCBI reference ({ncbi_ref_cag} CAG). "
            "This pattern is linked with a modestly increased androgen-receptor sensitivity."
        )
        comparison_band = "shorter_mild"
    elif delta >= 5:
        interpretation = (
            f"Your AR profile sits noticeably above the NCBI reference ({ncbi_ref_cag} CAG). "
            "Longer CAG repeats tend to be protective against AGA."
        )
        comparison_band = "longer_protective"
    elif delta >= 2:
        interpretation = (
            f"Your AR profile is mildly longer than the NCBI reference ({ncbi_ref_cag} CAG), "
            "which may have a small protective effect."
        )
        comparison_band = "longer_mild"
    else:
        interpretation = (
            f"Your AR profile is close to the NCBI reference ({ncbi_ref_cag} CAG), "
            "suggesting typical androgen-receptor sensitivity."
        )
        comparison_band = "near_reference"

    return {
        "ncbi_available":     ncbi_available,
        "ncbi_accession":     ncbi_accession,
        "ncbi_reference_cag": ncbi_ref_cag,
        "ncbi_description":   "Human androgen receptor mRNA, RefSeq reference",
        "user_value_type":    "measured" if measured else "estimated",
        "user_cag_min":       user_value_min,
        "user_cag_max":       user_value_max,
        "user_cag_midpoint":  user_midpoint,
        "user_risk_band":     inference.estimated_risk_band,
        "delta_vs_reference": delta,
        "comparison_band":    comparison_band,
        "interpretation":     interpretation,
        "inference_reasoning": inference.reasoning if not measured else [
            "Your CAG count was measured directly from your uploaded DNA sequence."
        ],
        "inference_confidence": inference.inference_confidence if not measured else "high",
    }
