"""
Clinical questionnaire scorer for Folliscope.
Implements scoring based on Norwood-Hamilton (1975), Ludwig (1977), and ALOPHA Index.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class Section1Data:
    age: int
    gender: str  # "pria" | "wanita"
    ethnicity: str  # "Asia" | "Kaukasian" | "Afrika" | "Lainnya"
    puberty_age: Optional[int] = None


@dataclass
class Section2Data:
    hair_loss_per_day: int  # 0-300
    loss_duration_months: int  # 0-60
    loss_pattern: str  # "none" | "diffuse" | "m-shape" | "vertex" | "patchy"
    thinning_areas: List[str]  # ["hairline", "crown", "temple", "all"]
    thinning_perception: int  # 1-10
    diameter_decreased: bool
    norwood_scale: Optional[int] = None  # 1-7 for male
    ludwig_scale: Optional[int] = None  # 1-3 for female


@dataclass
class Section3Data:
    hair_pull_count: Optional[int] = None  # 0-60, optional


@dataclass
class Section4Data:
    father_bald: bool = False
    father_bald_age: Optional[int] = None
    maternal_grandfather_bald: bool = False
    maternal_grandfather_bald_age: Optional[int] = None
    paternal_grandfather_bald: bool = False
    brothers_bald: bool = False
    mother_thinning: bool = False
    generations_bald: int = 0  # 0-4
    sisters_thinning: Optional[bool] = None


@dataclass
class Section5Data:
    stress_level: int  # 1-10
    sleep_hours: float  # 3-12
    smoking: bool = False
    cigarettes_per_day: int = 0
    alcohol_frequency: str = "tidak_pernah"  # "tidak_pernah"|"jarang"|"rutin"|"berat"
    diet_quality: str = "seimbang"  # "buruk"|"seimbang"|"sangat_baik"
    exercise_frequency: str = "sedang"  # "tidak_pernah"|"ringan"|"sedang"|"berat"
    aggressive_styling: bool = False
    medications: List[str] = field(default_factory=list)
    health_conditions: List[str] = field(default_factory=list)
    vitamin_deficiencies: List[str] = field(default_factory=list)


@dataclass
class ClinicalScoreBreakdown:
    norwood_ludwig_score: float
    pattern_area_score: float
    hair_pull_score: float
    loss_volume_score: float
    miniaturization_score: float
    duration_score: float
    total_clinical_score: float


@dataclass
class FamilyScoreBreakdown:
    maternal_grandfather_score: float
    father_score: float
    paternal_grandfather_score: float
    brothers_score: float
    mother_score: float
    generations_score: float
    total_family_score: float


@dataclass
class LifestyleScoreBreakdown:
    stress_score: float
    smoking_score: float
    sleep_score: float
    diet_score: float
    comorbidity_score: float
    total_lifestyle_score: float


@dataclass
class ClinicalAnalysisResult:
    clinical_score: float
    family_score: float
    lifestyle_score: float
    clinical_breakdown: ClinicalScoreBreakdown
    family_breakdown: FamilyScoreBreakdown
    lifestyle_breakdown: LifestyleScoreBreakdown
    age_modifier: float
    gender: str


def score_norwood_ludwig(s2: Section2Data) -> float:
    """Score the Norwood-Hamilton (male) or Ludwig (female) scale 0-100."""
    if s2.norwood_scale is not None:
        # Norwood I-VII
        scale_map = {1: 0, 2: 10, 3: 35, 4: 55, 5: 70, 6: 85, 7: 100}
        return float(scale_map.get(s2.norwood_scale, 0))
    elif s2.ludwig_scale is not None:
        # Ludwig I-III
        scale_map = {1: 30, 2: 65, 3: 100}
        return float(scale_map.get(s2.ludwig_scale, 0))
    return 0.0


def score_pattern_area(s2: Section2Data) -> float:
    """Score loss pattern and affected areas 0-100."""
    pattern_scores = {
        "none": 0,
        "diffuse": 20,
        "patchy": 30,
        "m-shape": 70,
        "vertex": 65,
        "m-shape-vertex": 90,
    }
    pattern_score = float(pattern_scores.get(s2.loss_pattern, 0))

    # Area multiplier
    area_bonus = 0.0
    area_weights = {"hairline": 0.3, "crown": 0.4, "temple": 0.2, "all": 1.0}
    for area in s2.thinning_areas:
        area_bonus += area_weights.get(area, 0)
    area_bonus = min(area_bonus, 1.0) * 20  # max 20 bonus points

    # Perception score contribution
    perception_score = (s2.thinning_perception - 1) / 9.0 * 15.0  # 0-15 points

    total = min(pattern_score + area_bonus + perception_score, 100.0)
    return total


def score_hair_pull(s3: Section3Data) -> float:
    """Score hair pull test 0-100. >6 out of 60 = active shedding."""
    if s3.hair_pull_count is None:
        return 0.0  # Not tested — neutral
    count = s3.hair_pull_count
    if count <= 3:
        return 0.0
    elif count <= 6:
        return 20.0
    elif count <= 10:
        return 50.0
    elif count <= 20:
        return 75.0
    else:
        return 100.0


def score_loss_volume(s2: Section2Data) -> float:
    """Score daily hair loss volume 0-100."""
    v = s2.hair_loss_per_day
    if v <= 50:
        return 0.0
    elif v <= 100:
        return 15.0
    elif v <= 150:
        return 40.0
    elif v <= 200:
        return 65.0
    elif v <= 250:
        return 85.0
    else:
        return 100.0


def score_miniaturization(s2: Section2Data) -> float:
    """Score miniaturization indicator 0-100."""
    return 75.0 if s2.diameter_decreased else 0.0


def score_duration(s2: Section2Data) -> float:
    """Score duration of symptoms 0-100. Chronic = higher risk of AGA (not reversible effluvium)."""
    m = s2.loss_duration_months
    if m <= 1:
        return 10.0
    elif m <= 3:
        return 25.0
    elif m <= 6:
        return 45.0
    elif m <= 12:
        return 65.0
    elif m <= 24:
        return 80.0
    else:
        return 95.0


def calculate_clinical_score(s1: Section1Data, s2: Section2Data, s3: Section3Data) -> ClinicalScoreBreakdown:
    """
    Calculate clinical score from questionnaire sections 1-3.
    Weights: Norwood/Ludwig 35%, Pattern+Area 20%, Pull test 15%, Volume 10%, Miniaturization 10%, Duration 10%
    """
    nl = score_norwood_ludwig(s2)
    pa = score_pattern_area(s2)
    pt = score_hair_pull(s3)
    lv = score_loss_volume(s2)
    mi = score_miniaturization(s2)
    du = score_duration(s2)

    total = (0.35 * nl + 0.20 * pa + 0.15 * pt + 0.10 * lv + 0.10 * mi + 0.10 * du)

    return ClinicalScoreBreakdown(
        norwood_ludwig_score=nl,
        pattern_area_score=pa,
        hair_pull_score=pt,
        loss_volume_score=lv,
        miniaturization_score=mi,
        duration_score=du,
        total_clinical_score=min(max(total, 0.0), 100.0)
    )


def calculate_family_score(s4: Section4Data) -> FamilyScoreBreakdown:
    """
    Calculate family history score 0-100.
    AR is X-linked: maternal grandfather is most important.
    Weights: maternal_gf 35%, father 25%, paternal_gf 15%, brothers 10%, mother 8%, generations 7%
    """
    # Maternal grandfather — X-linked: son inherits X from mother, mother from her father
    mat_gf = 100.0 if s4.maternal_grandfather_bald else 0.0
    # Early onset modifier
    if s4.maternal_grandfather_bald and s4.maternal_grandfather_bald_age:
        if s4.maternal_grandfather_bald_age < 30:
            mat_gf = min(mat_gf * 1.2, 100.0)

    father = 80.0 if s4.father_bald else 0.0
    if s4.father_bald and s4.father_bald_age:
        if s4.father_bald_age < 30:
            father = min(father * 1.15, 100.0)

    pat_gf = 60.0 if s4.paternal_grandfather_bald else 0.0
    brothers = 70.0 if s4.brothers_bald else 0.0
    mother = 50.0 if s4.mother_thinning else 0.0
    generations = min(s4.generations_bald / 4.0, 1.0) * 100.0

    total = (0.35 * mat_gf + 0.25 * father + 0.15 * pat_gf +
             0.10 * brothers + 0.08 * mother + 0.07 * generations)

    return FamilyScoreBreakdown(
        maternal_grandfather_score=mat_gf,
        father_score=father,
        paternal_grandfather_score=pat_gf,
        brothers_score=brothers,
        mother_score=mother,
        generations_score=generations,
        total_family_score=min(max(total, 0.0), 100.0)
    )


def calculate_lifestyle_score(s5: Section5Data) -> LifestyleScoreBreakdown:
    """
    Calculate lifestyle risk score 0-100.
    Weights: comorbidities 25%, stress 25%, smoking 20%, diet+exercise 15%, sleep 15%
    """
    # Stress
    stress = (s5.stress_level - 1) / 9.0 * 100.0

    # Smoking
    if not s5.smoking:
        smoking = 0.0
    elif s5.cigarettes_per_day <= 5:
        smoking = 40.0
    elif s5.cigarettes_per_day <= 10:
        smoking = 65.0
    elif s5.cigarettes_per_day <= 20:
        smoking = 80.0
    else:
        smoking = 100.0

    # Sleep
    if s5.sleep_hours >= 7:
        sleep = 0.0
    elif s5.sleep_hours >= 6:
        sleep = 30.0
    elif s5.sleep_hours >= 5:
        sleep = 60.0
    else:
        sleep = 90.0

    # Diet and exercise
    diet_scores = {"sangat_baik": 0, "seimbang": 20, "buruk": 70}
    exercise_scores = {"berat": 0, "sedang": 15, "ringan": 35, "tidak_pernah": 60}
    diet_ex = (diet_scores.get(s5.diet_quality, 20) + exercise_scores.get(s5.exercise_frequency, 15)) / 2.0

    # Comorbidities: PCOS, metabolic, thyroid, anemia, autoimmune
    high_risk_conditions = {"pcos", "sindrom_metabolik", "gangguan_tiroid", "anemia", "autoimun"}
    matched = sum(1 for c in s5.health_conditions if c.lower().replace(" ", "_") in high_risk_conditions)
    # Medications: steroids, antidepressants
    risky_meds = {"steroid", "antidepresan", "antihipertensi", "kontrasepsi"}
    med_risk = sum(1 for m in s5.medications if m.lower() in risky_meds)
    # Vitamin deficiencies
    vit_risk = len([v for v in s5.vitamin_deficiencies if v.lower() not in {"none", "tidak_tahu"}])

    comorbidity = min((matched * 25 + med_risk * 15 + vit_risk * 10), 100.0)

    # Aggressive styling modifier
    if s5.aggressive_styling:
        comorbidity = min(comorbidity + 10, 100.0)

    total = (0.25 * comorbidity + 0.25 * stress + 0.20 * smoking + 0.15 * diet_ex + 0.15 * sleep)

    return LifestyleScoreBreakdown(
        stress_score=stress,
        smoking_score=smoking,
        sleep_score=sleep,
        diet_score=diet_ex,
        comorbidity_score=comorbidity,
        total_lifestyle_score=min(max(total, 0.0), 100.0)
    )


def get_age_modifier(age: int, gender: str) -> float:
    """Age modifier: early onset (younger age with symptoms) = stronger genetic signal."""
    if age < 25:
        return 1.15
    elif age < 30:
        return 1.08
    elif age < 40:
        return 1.0
    elif age < 50:
        return 0.95
    else:
        return 0.90


def run_clinical_analysis(
    s1: Section1Data,
    s2: Section2Data,
    s3: Section3Data,
    s4: Section4Data,
    s5: Section5Data
) -> ClinicalAnalysisResult:
    """Run full clinical analysis pipeline."""
    clinical_bd = calculate_clinical_score(s1, s2, s3)
    family_bd = calculate_family_score(s4)
    lifestyle_bd = calculate_lifestyle_score(s5)
    age_mod = get_age_modifier(s1.age, s1.gender)

    return ClinicalAnalysisResult(
        clinical_score=clinical_bd.total_clinical_score,
        family_score=family_bd.total_family_score,
        lifestyle_score=lifestyle_bd.total_lifestyle_score,
        clinical_breakdown=clinical_bd,
        family_breakdown=family_bd,
        lifestyle_breakdown=lifestyle_bd,
        age_modifier=age_mod,
        gender=s1.gender
    )
