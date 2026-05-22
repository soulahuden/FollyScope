"""
Hybrid Polygenic Risk Score (PRS) calculator for BaldGuard.
Combines genetic + clinical + family + lifestyle components.
"""

from dataclasses import dataclass
from typing import Optional, Dict

from .reference_data import RISK_CATEGORIES, RECOMMENDATIONS
from .analyzer import GeneticAnalysisResult
from .clinical_analyzer import ClinicalAnalysisResult


@dataclass
class RiskScoreResult:
    hybrid_score: float
    genetic_score: float
    clinical_score: float
    family_score: float
    lifestyle_score: float
    risk_category: str
    risk_color: str
    risk_description: str
    analysis_type: str  # "hybrid" | "clinical_only" | "genetic_only"
    recommendations: list
    component_contributions: Dict[str, float]


def calculate_hybrid_score(
    genetic: Optional[GeneticAnalysisResult],
    clinical: ClinicalAnalysisResult
) -> float:
    """
    HybridScore = 0.45 * Genetic + 0.30 * Clinical + 0.15 * Family + 0.10 * Lifestyle
    Applied age modifier to final score.
    """
    g = genetic.genetic_score if genetic else 0.0
    c = clinical.clinical_score
    f = clinical.family_score
    l = clinical.lifestyle_score

    score = 0.45 * g + 0.30 * c + 0.15 * f + 0.10 * l
    # Apply age modifier
    score *= clinical.age_modifier
    return min(max(score, 0.0), 100.0)


def calculate_clinical_only_score(clinical: ClinicalAnalysisResult) -> float:
    """
    ClinicalOnlyScore = 0.55 * Clinical + 0.30 * Family + 0.15 * Lifestyle
    """
    c = clinical.clinical_score
    f = clinical.family_score
    l = clinical.lifestyle_score
    score = 0.55 * c + 0.30 * f + 0.15 * l
    score *= clinical.age_modifier
    return min(max(score, 0.0), 100.0)


def get_risk_category(score: float) -> tuple:
    """Map score to risk category tuple (name, color, description)."""
    for (low, high), (name, color, desc) in RISK_CATEGORIES.items():
        if low <= score <= high:
            return name, color, desc
    return "SANGAT_TINGGI", "#e74c3c", "Risiko sangat tinggi"


def calculate_risk_score(
    genetic: Optional[GeneticAnalysisResult],
    clinical: ClinicalAnalysisResult
) -> RiskScoreResult:
    """Main risk score calculation entry point."""
    has_genetic = genetic is not None and (genetic.has_sequence_data or genetic.has_snp_data)

    if has_genetic:
        analysis_type = "hybrid"
        hybrid_score = calculate_hybrid_score(genetic, clinical)
        genetic_score = genetic.genetic_score
        contributions = {
            "Genetik": round(0.45 * genetic_score, 1),
            "Klinis": round(0.30 * clinical.clinical_score, 1),
            "Keluarga": round(0.15 * clinical.family_score, 1),
            "Gaya Hidup": round(0.10 * clinical.lifestyle_score, 1),
        }
    else:
        analysis_type = "clinical_only"
        hybrid_score = calculate_clinical_only_score(clinical)
        genetic_score = 0.0
        contributions = {
            "Klinis": round(0.55 * clinical.clinical_score, 1),
            "Keluarga": round(0.30 * clinical.family_score, 1),
            "Gaya Hidup": round(0.15 * clinical.lifestyle_score, 1),
        }

    category, color, desc = get_risk_category(hybrid_score)
    recs = RECOMMENDATIONS.get(category, [])

    return RiskScoreResult(
        hybrid_score=round(hybrid_score, 1),
        genetic_score=round(genetic_score, 1),
        clinical_score=round(clinical.clinical_score, 1),
        family_score=round(clinical.family_score, 1),
        lifestyle_score=round(clinical.lifestyle_score, 1),
        risk_category=category,
        risk_color=color,
        risk_description=desc,
        analysis_type=analysis_type,
        recommendations=recs,
        component_contributions=contributions
    )
