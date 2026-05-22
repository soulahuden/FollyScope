"""
FastAPI REST API for BaldGuard.
Exposes endpoints for genetic and clinical analysis.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List, Any
from datetime import datetime
import traceback

from .reference_data import SNP_DATABASE, RECOMMENDATIONS
from .analyzer import run_genetic_analysis, parse_tsv_genotypes
from .clinical_analyzer import (
    Section1Data, Section2Data, Section3Data, Section4Data, Section5Data,
    run_clinical_analysis
)
from .risk_score import calculate_risk_score
from .ncbi import fetch_ar_reference
from .parser_23andme import parse_23andme

router = APIRouter(prefix="/api", tags=["BaldGuard API"])


# ── Pydantic request/response models ──────────────────────────────────────────

class Section1Input(BaseModel):
    age: int = Field(..., ge=15, le=80)
    gender: str = Field(..., pattern="^(pria|wanita)$")
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
    father_bald_age: Optional[int] = Field(default=None, ge=20, le=90)
    maternal_grandfather_bald: bool = False
    maternal_grandfather_bald_age: Optional[int] = Field(default=None, ge=20, le=90)
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
    alcohol_frequency: str = Field(default="tidak_pernah")
    diet_quality: str = Field(default="seimbang")
    exercise_frequency: str = Field(default="sedang")
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


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "BaldGuard API", "timestamp": datetime.now().isoformat()}


@router.get("/snp-database")
async def get_snp_database():
    """Return the full SNP reference database."""
    return {
        "snps": [
            {
                "rs_id": s.rs_id, "gene": s.gene, "chromosome": s.chromosome,
                "risk_allele": s.risk_allele, "ref_allele": s.ref_allele,
                "odds_ratio": s.odds_ratio, "prs_weight": s.prs_weight,
                "description": s.description, "function": s.function
            }
            for s in SNP_DATABASE
        ],
        "total": len(SNP_DATABASE)
    }


@router.post("/analyze")
async def analyze(request: AnalyzeRequest):
    """
    Main analysis endpoint. Accepts genetic + clinical data and returns risk score.
    """
    try:
        # Genetic analysis
        genetic_result = None
        if request.genetic_data:
            snp_genotypes = request.genetic_data.snp_genotypes or {}
            fasta = request.genetic_data.fasta_sequence
            if fasta or snp_genotypes:
                genetic_result = run_genetic_analysis(
                    fasta_text=fasta,
                    snp_genotypes=snp_genotypes
                )

        # Clinical analysis
        s1 = Section1Data(
            age=request.section1.age,
            gender=request.section1.gender,
            ethnicity=request.section1.ethnicity,
            puberty_age=request.section1.puberty_age
        )
        s2 = Section2Data(
            hair_loss_per_day=request.section2.hair_loss_per_day,
            loss_duration_months=request.section2.loss_duration_months,
            loss_pattern=request.section2.loss_pattern,
            thinning_areas=request.section2.thinning_areas,
            thinning_perception=request.section2.thinning_perception,
            diameter_decreased=request.section2.diameter_decreased,
            norwood_scale=request.section2.norwood_scale,
            ludwig_scale=request.section2.ludwig_scale
        )
        s3 = Section3Data(hair_pull_count=request.section3.hair_pull_count)
        s4 = Section4Data(
            father_bald=request.section4.father_bald,
            father_bald_age=request.section4.father_bald_age,
            maternal_grandfather_bald=request.section4.maternal_grandfather_bald,
            maternal_grandfather_bald_age=request.section4.maternal_grandfather_bald_age,
            paternal_grandfather_bald=request.section4.paternal_grandfather_bald,
            brothers_bald=request.section4.brothers_bald,
            mother_thinning=request.section4.mother_thinning,
            generations_bald=request.section4.generations_bald,
            sisters_thinning=request.section4.sisters_thinning
        )
        s5 = Section5Data(
            stress_level=request.section5.stress_level,
            sleep_hours=request.section5.sleep_hours,
            smoking=request.section5.smoking,
            cigarettes_per_day=request.section5.cigarettes_per_day,
            alcohol_frequency=request.section5.alcohol_frequency,
            diet_quality=request.section5.diet_quality,
            exercise_frequency=request.section5.exercise_frequency,
            aggressive_styling=request.section5.aggressive_styling,
            medications=request.section5.medications,
            health_conditions=request.section5.health_conditions,
            vitamin_deficiencies=request.section5.vitamin_deficiencies
        )

        clinical_result = run_clinical_analysis(s1, s2, s3, s4, s5)
        risk_result = calculate_risk_score(genetic_result, clinical_result)

        # Build response
        response = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "analysis_type": risk_result.analysis_type,
            "scores": {
                "hybrid_score": risk_result.hybrid_score,
                "genetic_score": risk_result.genetic_score,
                "clinical_score": risk_result.clinical_score,
                "family_score": risk_result.family_score,
                "lifestyle_score": risk_result.lifestyle_score
            },
            "risk_category": risk_result.risk_category,
            "risk_color": risk_result.risk_color,
            "risk_description": risk_result.risk_description,
            "component_contributions": risk_result.component_contributions,
            "recommendations": risk_result.recommendations,
            "disclaimer": "Hasil ini adalah estimasi risiko berdasarkan data yang diberikan dan TIDAK menggantikan diagnosis medis profesional. Selalu konsultasikan dengan dokter atau dermatolog untuk evaluasi klinis.",
        }

        if genetic_result:
            response["genetic_details"] = {
                "cag_repeats": genetic_result.cag_result.count,
                "cag_risk_level": genetic_result.cag_result.risk_level,
                "cag_interpretation": genetic_result.cag_result.interpretation,
                "ggn_repeats": genetic_result.ggn_result.count,
                "ggn_risk_level": genetic_result.ggn_result.risk_level,
                "ggn_interpretation": genetic_result.ggn_result.interpretation,
                "sequence_length": genetic_result.sequence_length,
                "snp_results": [
                    {
                        "rs_id": s.rs_id, "gene": s.gene,
                        "user_allele": s.user_allele,
                        "risk_allele": s.risk_allele,
                        "status": s.status,
                        "odds_ratio": s.odds_ratio,
                        "contribution": round(s.contribution, 3)
                    }
                    for s in genetic_result.snp_results
                ]
            }

        response["clinical_details"] = {
            "norwood_ludwig_score": clinical_result.clinical_breakdown.norwood_ludwig_score,
            "pattern_area_score": clinical_result.clinical_breakdown.pattern_area_score,
            "hair_pull_score": clinical_result.clinical_breakdown.hair_pull_score,
            "loss_volume_score": clinical_result.clinical_breakdown.loss_volume_score,
            "miniaturization_score": clinical_result.clinical_breakdown.miniaturization_score,
            "duration_score": clinical_result.clinical_breakdown.duration_score,
            "family_breakdown": {
                "maternal_grandfather": clinical_result.family_breakdown.maternal_grandfather_score,
                "father": clinical_result.family_breakdown.father_score,
                "paternal_grandfather": clinical_result.family_breakdown.paternal_grandfather_score,
                "brothers": clinical_result.family_breakdown.brothers_score,
                "mother": clinical_result.family_breakdown.mother_score,
                "generations": clinical_result.family_breakdown.generations_score,
            },
            "lifestyle_breakdown": {
                "stress": clinical_result.lifestyle_breakdown.stress_score,
                "smoking": clinical_result.lifestyle_breakdown.smoking_score,
                "sleep": clinical_result.lifestyle_breakdown.sleep_score,
                "diet_exercise": clinical_result.lifestyle_breakdown.diet_score,
                "comorbidities": clinical_result.lifestyle_breakdown.comorbidity_score,
            }
        }

        return JSONResponse(content=response)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analisis gagal: {str(e)}")


@router.post("/analyze/fasta-upload")
async def analyze_fasta_upload(file: UploadFile = File(...)):
    """Upload and parse a FASTA file, return sequence info."""
    if not file.filename.endswith(('.fasta', '.fa', '.txt')):
        raise HTTPException(status_code=400, detail="File harus berformat .fasta, .fa, atau .txt")
    content = await file.read()
    fasta_text = content.decode('utf-8')
    from .analyzer import parse_fasta, count_cag_repeats, count_ggn_repeats
    sequence = parse_fasta(fasta_text)
    if not sequence:
        raise HTTPException(status_code=400, detail="Tidak dapat membaca sekuens dari file FASTA")
    cag = count_cag_repeats(sequence)
    ggn = count_ggn_repeats(sequence)
    return {
        "success": True,
        "sequence_length": len(sequence),
        "cag_repeats": cag.count,
        "cag_risk_level": cag.risk_level,
        "ggn_repeats": ggn.count,
        "ggn_risk_level": ggn.risk_level,
        "sequence_preview": sequence[:100] + "..." if len(sequence) > 100 else sequence
    }


# ── NCBI endpoint ──────────────────────────────────────────────────────────────

@router.get("/ncbi/ar-reference")
async def get_ar_reference():
    """
    Ambil informasi sekuens referensi gen AR dari NCBI RefSeq (NM_000044.6).
    Hasil di-cache 1 jam untuk menghindari rate-limit NCBI.
    """
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
            "Sekuens referensi AR (NM_000044.6) dari NCBI RefSeq. "
            "Jumlah CAG pada sekuens referensi ini adalah baseline normal — "
            "bandingkan dengan jumlah CAG pengguna untuk konteks risiko."
        ),
    }


# ── 23andMe upload endpoint ────────────────────────────────────────────────────

@router.post("/analyze/23andme-upload")
async def analyze_23andme_upload(file: UploadFile = File(...)):
    """
    Upload file raw data 23andMe (.txt) dan ekstrak 9 SNP AGA panel.
    Mengembalikan genotype yang siap dipakai di endpoint /api/analyze.
    """
    if not file.filename.lower().endswith((".txt", ".csv", ".zip")):
        raise HTTPException(
            status_code=400,
            detail="File harus berformat .txt (raw data 23andMe)"
        )

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    result = parse_23andme(text)

    # Buat ringkasan per SNP untuk tampilan frontend
    snp_summary = []
    for snp_record in SNP_DATABASE:
        rs_id  = snp_record.rs_id
        parsed = result.parsed_snps.get(rs_id)
        if parsed and not parsed.is_no_call:
            status = (
                "HOMOZYGOUS_RISK" if parsed.risk_dosage == 1.0
                else "HETEROZYGOUS"  if parsed.risk_dosage == 0.5
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
                "genotype":    parsed.genotype if parsed else "—",
                "risk_allele": snp_record.risk_allele,
                "status":      "NO_CALL" if (parsed and parsed.is_no_call) else "NOT_FOUND",
                "risk_dosage": 0.0,
            })

    return {
        "success":         True,
        "source":          "23andMe raw data",
        "snp_genotypes":   result.snp_genotypes,
        "snp_summary":     snp_summary,
        "stats": {
            "total_in_panel": result.total_in_panel,
            "found":          result.found_count,
            "callable":       result.callable_count,
            "no_call":        result.no_call_count,
            "missing":        result.missing_count,
        },
        "note": (
            "SNP heterozygous dilaporkan sebagai risk (conservative). "
            "Salin 'snp_genotypes' ke request /api/analyze untuk analisis penuh."
        ),
    }
