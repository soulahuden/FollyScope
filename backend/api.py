"""
FastAPI REST API for Folliscope.

Public-facing endpoints accept English values (male/female, balanced, etc.)
and the main /analyze endpoint always integrates the NCBI AR reference
plus a clinical-only phenotype inference, so general users without DNA
data still get an interpretable, education-friendly genetic comparison.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .analyzer import run_genetic_analysis
from .clinical_analyzer import (
    Section1Data,
    Section2Data,
    Section3Data,
    Section4Data,
    Section5Data,
    run_clinical_analysis,
)
from .ncbi import fetch_ar_reference
from .parser_23andme import parse_23andme
from .phenotype_inference import (
    NCBI_REFERENCE_CAG,
    build_ncbi_comparison,
    compute_confidence,
    infer_phenotype_profile,
)
from .reference_data import SNP_DATABASE
from .risk_score import calculate_risk_score

router = APIRouter(prefix="/api", tags=["Folliscope API"])


# ── Value translation (English in / Indonesian internal) ──────────────────────

_GENDER_MAP = {"male": "pria", "female": "wanita", "pria": "pria", "wanita": "wanita"}

_DIET_MAP = {
    "great": "sangat_baik", "balanced": "seimbang", "poor": "buruk",
    "sangat_baik": "sangat_baik", "seimbang": "seimbang", "buruk": "buruk",
}

_EXERCISE_MAP = {
    "none": "tidak_pernah", "light": "ringan", "moderate": "sedang", "heavy": "berat",
    "tidak_pernah": "tidak_pernah", "ringan": "ringan", "sedang": "sedang", "berat": "berat",
}

_ALCOHOL_MAP = {
    "never": "tidak_pernah", "rare": "jarang", "regular": "rutin", "heavy": "berat",
    "tidak_pernah": "tidak_pernah", "jarang": "jarang", "rutin": "rutin", "berat": "berat",
}

_PATTERN_MAP = {
    "none": "none", "diffuse": "diffuse", "patchy": "patchy",
    "m-shape": "m-shape", "m_shape": "m-shape",
    "vertex": "vertex", "m-shape-vertex": "m-shape-vertex",
}

_CATEGORY_LABELS = {
    "MINIMAL":       "Minimal",
    "RENDAH":        "Low",
    "SEDANG":        "Moderate",
    "TINGGI":        "High",
    "SANGAT_TINGGI": "Very High",
}

_CAG_RISK_LABELS = {
    "SANGAT_TINGGI":  "Very High",
    "TINGGI":         "High",
    "SEDANG":         "Moderate",
    "RENDAH":         "Low",
    "PROTEKTIF":      "Protective",
    "TIDAK_DIKETAHUI": "Unknown",
}

# Recommendations are stored under Indonesian keys; for English UI we add an
# English overlay. Keep concise, clinically defensible, and actionable.
_RECOMMENDATIONS_EN: Dict[str, List[str]] = {
    "MINIMAL": [
        "No specific intervention needed right now.",
        "Maintain a healthy lifestyle: sufficient sleep, balanced diet, regular exercise.",
        "Check on your hair condition periodically.",
        "Consider re-evaluating every 5 years or sooner if symptoms appear.",
    ],
    "RENDAH": [
        "Track your daily shedding, anything under ~100 hairs a day is normal.",
        "Prioritize protein, biotin, zinc, vitamin D, and iron in your diet.",
        "Keep your scalp healthy with a mild, appropriate shampoo.",
        "Manage stress and aim for 7-8 hours of sleep nightly.",
        "Consider a dermatology consult if you notice any visible change.",
    ],
    "SEDANG": [
        "Early warning: moderate susceptibility detected.",
        "A clinical trichoscopy and DHT level test would help confirm AR involvement.",
        "Consider DHT-blocking shampoos (ketoconazole 2%, saw palmetto).",
        "Targeted supplements: biotin, zinc, vitamin D, omega-3.",
        "Avoid aggressive styling, bleaching, and tight ponytails.",
        "Re-evaluate every 12 months.",
    ],
    "TINGGI": [
        "Warning: AGA risk is high, early intervention is strongly recommended.",
        "See a dermatologist within the next 1-3 months.",
        "Topical minoxidil 5% (available over the counter) is a reasonable first step.",
        "For men: ask your doctor about prescription oral finasteride 1 mg daily.",
        "Address modifiable factors: stress, sleep, smoking, nutrition.",
        "Consider Low-Level Laser Therapy (LLLT) as an adjunct.",
        "Schedule a follow-up trichoscopy every 6 months.",
    ],
    "SANGAT_TINGGI": [
        "Critical: very high AGA risk profile.",
        "See a dermatologist or trichologist as soon as possible.",
        "Combination therapy is typically required: minoxidil + finasteride (for men) and topical anti-androgens (for women).",
        "PRP (Platelet-Rich Plasma) injections may be considered.",
        "Long-term hair-transplant planning may be relevant if progression continues.",
        "Aggressively address comorbidities (PCOS, thyroid, metabolic syndrome).",
        "Tight monitoring every 3 months in the first year.",
    ],
}


# ── Pydantic request models ────────────────────────────────────────────────────

class Section1Input(BaseModel):
    age: int = Field(..., ge=15, le=80)
    gender: str = Field(..., pattern="^(male|female|pria|wanita)$")
    ethnicity: str = Field(default="Asia")
    puberty_age: Optional[int] = Field(default=None, ge=9, le=18)


class Section2Input(BaseModel):
    hair_loss_per_day: int = Field(default=80, ge=0, le=300)
    loss_duration_months: int = Field(default=0, ge=0, le=60)
    loss_pattern: str = Field(default="none")
    thinning_areas: List[str] = Field(default_factory=list)
    thinning_perception: int = Field(default=1, ge=1, le=10)
    diameter_decreased: bool = Field(default=False)
    norwood_scale: Optional[int] = Field(default=None, ge=1, le=7)
    ludwig_scale: Optional[int] = Field(default=None, ge=1, le=3)


class Section3Input(BaseModel):
    hair_pull_count: Optional[int] = Field(default=None, ge=0, le=60)


class Section4Input(BaseModel):
    father_bald: bool = False
    father_bald_age: Optional[int] = Field(default=None, ge=10, le=90)
    maternal_grandfather_bald: bool = False
    maternal_grandfather_bald_age: Optional[int] = Field(default=None, ge=10, le=90)
    paternal_grandfather_bald: bool = False
    brothers_bald: bool = False
    mother_thinning: bool = False
    generations_bald: int = Field(default=0, ge=0, le=4)
    sisters_thinning: Optional[bool] = None


class Section5Input(BaseModel):
    stress_level: int = Field(default=5, ge=1, le=10)
    sleep_hours: float = Field(default=7.0, ge=3.0, le=12.0)
    smoking: bool = False
    cigarettes_per_day: int = Field(default=0, ge=0, le=100)
    alcohol_frequency: str = Field(default="never")
    diet_quality: str = Field(default="balanced")
    exercise_frequency: str = Field(default="moderate")
    aggressive_styling: bool = False
    medications: List[str] = Field(default_factory=list)
    health_conditions: List[str] = Field(default_factory=list)
    vitamin_deficiencies: List[str] = Field(default_factory=list)


class GeneticInput(BaseModel):
    fasta_sequence: Optional[str] = None
    snp_genotypes: Optional[Dict[str, str]] = None


class AnalyzeRequest(BaseModel):
    genetic_data: Optional[GeneticInput] = None
    section1: Section1Input
    section2: Section2Input
    section3: Section3Input = Field(default_factory=Section3Input)
    section4: Section4Input = Field(default_factory=Section4Input)
    section5: Section5Input = Field(default_factory=Section5Input)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _norm_pattern(p: str) -> str:
    return _PATTERN_MAP.get(p, "none")


def _build_section_data(req: AnalyzeRequest):
    s1 = Section1Data(
        age=req.section1.age,
        gender=_GENDER_MAP.get(req.section1.gender, "pria"),
        ethnicity=req.section1.ethnicity,
        puberty_age=req.section1.puberty_age,
    )
    s2 = Section2Data(
        hair_loss_per_day=req.section2.hair_loss_per_day,
        loss_duration_months=req.section2.loss_duration_months,
        loss_pattern=_norm_pattern(req.section2.loss_pattern),
        thinning_areas=req.section2.thinning_areas,
        thinning_perception=req.section2.thinning_perception,
        diameter_decreased=req.section2.diameter_decreased,
        norwood_scale=req.section2.norwood_scale,
        ludwig_scale=req.section2.ludwig_scale,
    )
    s3 = Section3Data(hair_pull_count=req.section3.hair_pull_count)
    s4 = Section4Data(
        father_bald=req.section4.father_bald,
        father_bald_age=req.section4.father_bald_age,
        maternal_grandfather_bald=req.section4.maternal_grandfather_bald,
        maternal_grandfather_bald_age=req.section4.maternal_grandfather_bald_age,
        paternal_grandfather_bald=req.section4.paternal_grandfather_bald,
        brothers_bald=req.section4.brothers_bald,
        mother_thinning=req.section4.mother_thinning,
        generations_bald=req.section4.generations_bald,
        sisters_thinning=req.section4.sisters_thinning,
    )
    s5 = Section5Data(
        stress_level=req.section5.stress_level,
        sleep_hours=req.section5.sleep_hours,
        smoking=req.section5.smoking,
        cigarettes_per_day=req.section5.cigarettes_per_day,
        alcohol_frequency=_ALCOHOL_MAP.get(req.section5.alcohol_frequency, "tidak_pernah"),
        diet_quality=_DIET_MAP.get(req.section5.diet_quality, "seimbang"),
        exercise_frequency=_EXERCISE_MAP.get(req.section5.exercise_frequency, "sedang"),
        aggressive_styling=req.section5.aggressive_styling,
        medications=req.section5.medications,
        health_conditions=req.section5.health_conditions,
        vitamin_deficiencies=req.section5.vitamin_deficiencies,
    )
    return s1, s2, s3, s4, s5


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "Folliscope API", "timestamp": datetime.now().isoformat()}


@router.get("/snp-database")
async def get_snp_database():
    return {
        "snps": [
            {
                "rs_id":       s.rs_id,
                "gene":        s.gene,
                "chromosome":  s.chromosome,
                "risk_allele": s.risk_allele,
                "ref_allele":  s.ref_allele,
                "odds_ratio":  s.odds_ratio,
                "prs_weight":  s.prs_weight,
                "description": s.description,
                "function":    s.function,
            }
            for s in SNP_DATABASE
        ],
        "total": len(SNP_DATABASE),
    }


@router.post("/analyze")
async def analyze(request: AnalyzeRequest):
    """
    Main analysis endpoint.

    Always performs:
      - Clinical scoring (questionnaire is the required input)
      - NCBI AR reference fetch (educational baseline; gracefully falls back)
      - Phenotype-to-genotype inference (CAG range estimate from clinical signals)
      - User-friendly NCBI vs. user comparison
      - Transparent confidence reporting

    Genetic data (FASTA / SNP / 23andMe) is an optional advanced path that
    raises confidence, it does not gate the analysis.
    """
    try:
        # 1. Optional genetic analysis (advanced path)
        genetic_result = None
        if request.genetic_data:
            snp_genotypes = request.genetic_data.snp_genotypes or {}
            fasta         = request.genetic_data.fasta_sequence
            if fasta or snp_genotypes:
                genetic_result = run_genetic_analysis(
                    fasta_text=fasta,
                    snp_genotypes=snp_genotypes,
                )

        # 2. Clinical analysis (always)
        s1, s2, s3, s4, s5 = _build_section_data(request)
        clinical_result    = run_clinical_analysis(s1, s2, s3, s4, s5)
        risk_result        = calculate_risk_score(genetic_result, clinical_result)

        # 3. Phenotype inference (always)
        inference = infer_phenotype_profile(s1, clinical_result)

        # 4. NCBI reference fetch (always, graceful fallback)
        ncbi = fetch_ar_reference()
        ncbi_cag    = ncbi.cag_count if (ncbi.success and ncbi.cag_count > 0) else NCBI_REFERENCE_CAG
        ncbi_avail  = ncbi.success

        # 5. Build the user-friendly NCBI comparison block
        ncbi_comparison = build_ncbi_comparison(
            inference        = inference,
            genetic          = genetic_result,
            ncbi_ref_cag     = ncbi_cag,
            ncbi_accession   = ncbi.accession,
            ncbi_available   = ncbi_avail,
        )

        # 6. Confidence
        confidence = compute_confidence(genetic_result)

        # 7. Response
        category_en = _CATEGORY_LABELS.get(risk_result.risk_category, risk_result.risk_category)
        recs_en     = _RECOMMENDATIONS_EN.get(risk_result.risk_category, risk_result.recommendations)

        response: Dict[str, Any] = {
            "success":        True,
            "timestamp":      datetime.now().isoformat(),
            "analysis_type":  risk_result.analysis_type,
            "scores": {
                "hybrid_score":    risk_result.hybrid_score,
                "genetic_score":   risk_result.genetic_score,
                "clinical_score":  risk_result.clinical_score,
                "family_score":    risk_result.family_score,
                "lifestyle_score": risk_result.lifestyle_score,
            },
            "risk_category":           risk_result.risk_category,
            "risk_category_label":     category_en,
            "risk_color":              risk_result.risk_color,
            "risk_description":        _risk_description_en(risk_result.risk_category),
            "component_contributions": risk_result.component_contributions,
            "recommendations":         recs_en,
            "confidence": {
                "level":       confidence.level,
                "label":       confidence.label,
                "percent":     confidence.percent,
                "description": confidence.description,
                "inputs_used": confidence.inputs_used,
            },
            "ncbi_comparison":  ncbi_comparison,
            "ncbi_reference":   {
                "available":        ncbi_avail,
                "source":           ncbi.source,
                "accession":        ncbi.accession,
                "url":              ncbi.url,
                "description":      ncbi.description if ncbi_avail else "",
                "sequence_length":  ncbi.sequence_length if ncbi_avail else 0,
                "cag_count":        ncbi_cag,
                "sequence_preview": ncbi.sequence_preview if ncbi_avail else "",
                "fetched_at":       datetime.now().isoformat() if ncbi_avail else None,
            },
            "phenotype_inference": {
                "estimated_cag_min":      inference.estimated_cag_min,
                "estimated_cag_max":      inference.estimated_cag_max,
                "estimated_cag_midpoint": inference.estimated_cag_midpoint,
                "estimated_risk_band":    inference.estimated_risk_band,
                "confidence":             inference.inference_confidence,
                "reasoning":              inference.reasoning,
                "delta_vs_reference":     inference.delta_vs_reference,
            },
            "disclaimer": (
                "Educational risk assessment, not a medical diagnosis. "
                "For clinical evaluation, see a licensed dermatologist or trichologist."
            ),
        }

        # Clinical detail block (English keys for new UI; legacy keys kept for backward compat)
        cb = clinical_result.clinical_breakdown
        fb = clinical_result.family_breakdown
        lb = clinical_result.lifestyle_breakdown
        response["clinical_details"] = {
            "norwood_ludwig_score":  cb.norwood_ludwig_score,
            "pattern_area_score":    cb.pattern_area_score,
            "hair_pull_score":       cb.hair_pull_score,
            "loss_volume_score":     cb.loss_volume_score,
            "miniaturization_score": cb.miniaturization_score,
            "duration_score":        cb.duration_score,
            "family_breakdown": {
                "maternal_grandfather": fb.maternal_grandfather_score,
                "father":               fb.father_score,
                "paternal_grandfather": fb.paternal_grandfather_score,
                "brothers":             fb.brothers_score,
                "mother":               fb.mother_score,
                "generations":          fb.generations_score,
            },
            "lifestyle_breakdown": {
                "stress":        lb.stress_score,
                "smoking":       lb.smoking_score,
                "sleep":         lb.sleep_score,
                "diet_exercise": lb.diet_score,
                "comorbidities": lb.comorbidity_score,
            },
            "age_modifier": clinical_result.age_modifier,
        }

        if genetic_result:
            response["genetic_details"] = {
                "cag_repeats":         genetic_result.cag_result.count,
                "cag_risk_level":      genetic_result.cag_result.risk_level,
                "cag_risk_label":      _CAG_RISK_LABELS.get(genetic_result.cag_result.risk_level, ""),
                "cag_interpretation":  genetic_result.cag_result.interpretation,
                "ggn_repeats":         genetic_result.ggn_result.count,
                "ggn_risk_level":      genetic_result.ggn_result.risk_level,
                "ggn_interpretation":  genetic_result.ggn_result.interpretation,
                "sequence_length":     genetic_result.sequence_length,
                "snp_results": [
                    {
                        "rs_id":        s.rs_id,
                        "gene":         s.gene,
                        "user_allele":  s.user_allele,
                        "risk_allele":  s.risk_allele,
                        "status":       s.status,
                        "odds_ratio":   s.odds_ratio,
                        "contribution": round(s.contribution, 3),
                    }
                    for s in genetic_result.snp_results
                ],
            }

        return JSONResponse(content=response)

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}")


def _risk_description_en(category: str) -> str:
    return {
        "MINIMAL":       "Minimal risk profile detected.",
        "RENDAH":        "Low risk profile detected.",
        "SEDANG":        "Moderate risk profile detected, worth monitoring.",
        "TINGGI":        "High risk profile detected, early intervention recommended.",
        "SANGAT_TINGGI": "Very high risk profile detected, clinical consultation recommended.",
    }.get(category, "Risk profile assessed.")


# ── Advanced upload endpoints ─────────────────────────────────────────────────

@router.get("/ncbi/ar-reference")
async def get_ar_reference():
    """Standalone NCBI reference fetch (used by Database page / advanced flows)."""
    result = fetch_ar_reference()
    return {
        "success":          result.success,
        "accession":        result.accession,
        "description":      result.description,
        "sequence_length":  result.sequence_length,
        "cag_count":        result.cag_count,
        "cag_position":     result.cag_position,
        "sequence_preview": result.sequence_preview,
        "source":           result.source,
        "error":            result.error,
        "note": (
            "Reference AR sequence (NM_000044.6) from NCBI RefSeq. "
            "The CAG count of this reference serves as the educational baseline."
        ),
    }


@router.post("/analyze/23andme-upload")
async def analyze_23andme_upload(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".txt", ".csv", ".zip")):
        raise HTTPException(status_code=400, detail="File must be the 23andMe raw-data .txt format")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    result = parse_23andme(text)

    snp_summary = []
    for snp_record in SNP_DATABASE:
        rs_id  = snp_record.rs_id
        parsed = result.parsed_snps.get(rs_id)
        if parsed and not parsed.is_no_call:
            status = (
                "HOMOZYGOUS_RISK" if parsed.risk_dosage == 1.0
                else "HETEROZYGOUS" if parsed.risk_dosage == 0.5
                else "NORMAL"
            )
            snp_summary.append({
                "rs_id":       rs_id,
                "gene":        snp_record.gene,
                "genotype":    parsed.genotype,
                "risk_allele": snp_record.risk_allele,
                "status":      status,
                "risk_dosage": parsed.risk_dosage,
            })
        else:
            snp_summary.append({
                "rs_id":       rs_id,
                "gene":        snp_record.gene,
                "genotype":    parsed.genotype if parsed else ", ",
                "risk_allele": snp_record.risk_allele,
                "status":      "NO_CALL" if (parsed and parsed.is_no_call) else "NOT_FOUND",
                "risk_dosage": 0.0,
            })

    return {
        "success":        True,
        "source":         "23andMe raw data",
        "snp_genotypes":  result.snp_genotypes,
        "snp_summary":    snp_summary,
        "stats": {
            "total_in_panel": result.total_in_panel,
            "found":          result.found_count,
            "callable":       result.callable_count,
            "no_call":        result.no_call_count,
            "missing":        result.missing_count,
        },
        "note": (
            "Heterozygous SNPs are reported as risk (conservative). "
            "Copy 'snp_genotypes' into the /api/analyze request body for a full analysis."
        ),
    }
