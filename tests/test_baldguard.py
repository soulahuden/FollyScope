"""
Unit tests for BaldGuard — 45+ test cases covering:
  - CAG repeat counting and risk classification
  - GGN repeat counting and risk classification
  - SNP detection and scoring
  - Clinical score calculation
  - Family history scoring
  - Lifestyle scoring
  - Hybrid risk calculation and categorisation
  - FASTA / TSV parsing

Run: pytest tests/test_baldguard.py -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from backend.analyzer import (
    count_cag_repeats,
    count_ggn_repeats,
    analyze_snps,
    calculate_snp_score,
    calculate_genetic_score,
    parse_fasta,
    parse_tsv_genotypes,
    run_genetic_analysis,
)
from backend.clinical_analyzer import (
    Section1Data,
    Section2Data,
    Section3Data,
    Section4Data,
    Section5Data,
    calculate_clinical_score,
    calculate_family_score,
    calculate_lifestyle_score,
    run_clinical_analysis,
    score_norwood_ludwig,
    score_hair_pull,
)
from backend.risk_score import calculate_risk_score, get_risk_category
from backend.reference_data import SNP_DATABASE


# ── Shared helper sequences ──────────────────────────────────────────────────

# Flanking regions that contain no CAG or GGC runs
_FLANK_5 = "ATGTTTCTTATTATTTGAAAGCTGAAGAACATTTCGCGTGCTGACTAATTGTTATGATTTGCGAAGTCTGCAGTTTTTGCAT"
_FLANK_MID = "GCTCCGCATGCCGCAGAGCCCAGCGCCAGCCCCTGCTCATGACTGCTTCTTATTATTTGAAAT"
_FLANK_3 = "CATTTCAGCGTGCTGACTAATTGTTATGATTTGCGAAGTCTGCAGTTTTTGCAGCTCCC"

CAG_17 = _FLANK_5 + "CAG" * 17 + _FLANK_MID + "GGC" * 5 + _FLANK_3   # only 17 CAG
CAG_23 = _FLANK_5 + "CAG" * 23 + _FLANK_MID + "GGC" * 5 + _FLANK_3
CAG_29 = _FLANK_5 + "CAG" * 29 + _FLANK_MID + "GGC" * 5 + _FLANK_3
CAG_33 = _FLANK_5 + "CAG" * 33 + _FLANK_MID + "GGC" * 5 + _FLANK_3

GGN_18 = _FLANK_5 + "CAG" * 5 + _FLANK_MID + "GGC" * 18 + _FLANK_3
GGN_22 = _FLANK_5 + "CAG" * 5 + _FLANK_MID + "GGC" * 22 + _FLANK_3
GGN_23 = _FLANK_5 + "CAG" * 5 + _FLANK_MID + "GGC" * 23 + _FLANK_3

HIGH_RISK_SNP = {
    "rs6152": "G",
    "rs1385699": "C",
    "rs12558842": "G",
    "rs2497938": "C",
    "rs7349332": "T",
    "rs9479482": "C",
    "rs1160312": "A",
    "rs929626": "C",
    "rs523349": "G",
}

LOW_RISK_SNP = {
    "rs6152": "A",
    "rs1385699": "T",
    "rs12558842": "A",
    "rs2497938": "T",
    "rs7349332": "C",
    "rs9479482": "T",
    "rs1160312": "G",
    "rs929626": "G",
    "rs523349": "C",
}


# ── CAG repeat tests ─────────────────────────────────────────────────────────

class TestCAGRepeats:
    def test_cag_17_count(self):
        result = count_cag_repeats(CAG_17)
        assert result.count == 17

    def test_cag_23_count(self):
        result = count_cag_repeats(CAG_23)
        assert result.count == 23

    def test_cag_29_count(self):
        result = count_cag_repeats(CAG_29)
        assert result.count == 29

    def test_cag_33_count(self):
        result = count_cag_repeats(CAG_33)
        assert result.count == 33

    def test_cag_17_risk_level_sangat_tinggi(self):
        result = count_cag_repeats(CAG_17)
        assert result.risk_level == "SANGAT_TINGGI"

    def test_cag_23_risk_level_sedang(self):
        result = count_cag_repeats(CAG_23)
        assert result.risk_level == "SEDANG"

    def test_cag_29_risk_level_rendah(self):
        result = count_cag_repeats(CAG_29)
        assert result.risk_level == "RENDAH"

    def test_cag_33_risk_level_protektif(self):
        result = count_cag_repeats(CAG_33)
        assert result.risk_level == "PROTEKTIF"

    def test_cag_empty_sequence_count_zero(self):
        result = count_cag_repeats("")
        assert result.count == 0

    def test_cag_no_repeats_count_zero(self):
        result = count_cag_repeats("ATGATGATGATGATG")
        assert result.count == 0

    def test_cag_result_has_risk_score_attribute(self):
        result = count_cag_repeats(CAG_17)
        assert hasattr(result, "risk_score")

    def test_cag_high_risk_score_greater_than_low(self):
        high = count_cag_repeats(CAG_17)
        low = count_cag_repeats(CAG_33)
        assert high.risk_score > low.risk_score


# ── GGN repeat tests ─────────────────────────────────────────────────────────

class TestGGNRepeats:
    def test_ggn_18_count(self):
        result = count_ggn_repeats(GGN_18)
        assert result.count == 18

    def test_ggn_22_count(self):
        result = count_ggn_repeats(GGN_22)
        assert result.count == 22

    def test_ggn_23_count(self):
        result = count_ggn_repeats(GGN_23)
        assert result.count == 23

    def test_ggn_18_risk_level_sedang(self):
        # GGN=18 falls in range 18-23 which maps to SEDANG per GGN_THRESHOLDS
        result = count_ggn_repeats(GGN_18)
        assert result.risk_level == "SEDANG"

    def test_ggn_23_risk_level_sedang(self):
        result = count_ggn_repeats(GGN_23)
        assert result.risk_level == "SEDANG"

    def test_ggn_empty_sequence_count_zero(self):
        result = count_ggn_repeats("")
        assert result.count == 0

    def test_ggn_result_has_risk_score_attribute(self):
        result = count_ggn_repeats(GGN_23)
        assert hasattr(result, "risk_score")


# ── SNP detection and scoring tests ──────────────────────────────────────────

class TestSNPDetection:
    def test_all_risk_alleles_detected(self):
        results = analyze_snps(HIGH_RISK_SNP)
        risk_count = sum(1 for r in results if r.status == "RISK")
        assert risk_count == 9

    def test_all_normal_alleles_zero_risk(self):
        results = analyze_snps(LOW_RISK_SNP)
        risk_count = sum(1 for r in results if r.status == "RISK")
        assert risk_count == 0

    def test_empty_dict_all_unknown(self):
        results = analyze_snps({})
        assert all(r.status == "UNKNOWN" for r in results)

    def test_snp_score_max_for_all_risk(self):
        results = analyze_snps(HIGH_RISK_SNP)
        score = calculate_snp_score(results)
        assert score > 90.0

    def test_snp_score_zero_for_all_normal(self):
        results = analyze_snps(LOW_RISK_SNP)
        score = calculate_snp_score(results)
        assert score == 0.0

    def test_snp_score_between_bounds(self):
        mixed = dict(list(HIGH_RISK_SNP.items())[:5] + list(LOW_RISK_SNP.items())[5:])
        results = analyze_snps(mixed)
        score = calculate_snp_score(results)
        assert 0.0 <= score <= 100.0

    def test_snp_database_contains_nine_entries(self):
        assert len(SNP_DATABASE) == 9

    def test_snp_database_rs_ids_start_with_rs(self):
        # SNP_DATABASE is a list of SNPRecord dataclass objects
        for record in SNP_DATABASE:
            assert record.rs_id.startswith("rs")


# ── Clinical score tests ──────────────────────────────────────────────────────

class TestClinicalScore:
    def _make_high_clinical(self, norwood=6):
        s1 = Section1Data(age=30, gender="pria", ethnicity="Asia")
        s2 = Section2Data(
            hair_loss_per_day=200,
            loss_duration_months=24,
            loss_pattern="m-shape",
            thinning_areas=["hairline", "crown"],
            thinning_perception=9,
            diameter_decreased=True,
            norwood_scale=norwood,
        )
        s3 = Section3Data(hair_pull_count=15)
        return s1, s2, s3

    def _make_low_clinical(self):
        s1 = Section1Data(age=30, gender="pria", ethnicity="Asia")
        s2 = Section2Data(
            hair_loss_per_day=50,
            loss_duration_months=1,
            loss_pattern="none",
            thinning_areas=[],
            thinning_perception=1,
            diameter_decreased=False,
            norwood_scale=1,
        )
        s3 = Section3Data(hair_pull_count=2)
        return s1, s2, s3

    def test_high_norwood_gives_high_score(self):
        s1, s2, s3 = self._make_high_clinical(norwood=6)
        bd = calculate_clinical_score(s1, s2, s3)
        assert bd.total_clinical_score > 60

    def test_norwood_1_gives_low_score(self):
        s1, s2, s3 = self._make_low_clinical()
        bd = calculate_clinical_score(s1, s2, s3)
        assert bd.total_clinical_score < 30

    def test_hair_pull_positive_threshold(self):
        s3 = Section3Data(hair_pull_count=15)
        score = score_hair_pull(s3)
        assert score >= 75.0

    def test_hair_pull_normal_zero(self):
        s3 = Section3Data(hair_pull_count=3)
        score = score_hair_pull(s3)
        assert score == 0.0

    def test_clinical_score_bounded(self):
        s1, s2, s3 = self._make_high_clinical()
        bd = calculate_clinical_score(s1, s2, s3)
        assert 0.0 <= bd.total_clinical_score <= 100.0

    def test_norwood_score_increases_with_scale(self):
        scores = []
        for level in [1, 3, 5, 7]:
            s1 = Section1Data(age=35, gender="pria", ethnicity="Asia")
            s2 = Section2Data(
                hair_loss_per_day=100,
                loss_duration_months=6,
                loss_pattern="m-shape",
                thinning_areas=["hairline"],
                thinning_perception=5,
                diameter_decreased=True,
                norwood_scale=level,
            )
            s3 = Section3Data(hair_pull_count=5)
            bd = calculate_clinical_score(s1, s2, s3)
            scores.append(bd.total_clinical_score)
        assert scores == sorted(scores)


# ── Family history score tests ────────────────────────────────────────────────

class TestFamilyScore:
    def test_maternal_grandfather_outweighs_father_alone(self):
        s4_mat = Section4Data(maternal_grandfather_bald=True)
        s4_father = Section4Data(father_bald=True)
        assert calculate_family_score(s4_mat).total_family_score > \
               calculate_family_score(s4_father).total_family_score

    def test_no_family_history_score_zero(self):
        bd = calculate_family_score(Section4Data())
        assert bd.total_family_score == 0.0

    def test_full_family_history_high_score(self):
        s4 = Section4Data(
            father_bald=True,
            maternal_grandfather_bald=True,
            paternal_grandfather_bald=True,
            brothers_bald=True,
            mother_thinning=True,
            generations_bald=4,
        )
        bd = calculate_family_score(s4)
        assert bd.total_family_score > 70.0

    def test_family_score_bounded(self):
        s4 = Section4Data(
            father_bald=True,
            maternal_grandfather_bald=True,
            paternal_grandfather_bald=True,
            brothers_bald=True,
            mother_thinning=True,
            generations_bald=4,
        )
        bd = calculate_family_score(s4)
        assert 0.0 <= bd.total_family_score <= 100.0


# ── Lifestyle score tests ─────────────────────────────────────────────────────

class TestLifestyleScore:
    def test_high_stress_smoking_gives_high_score(self):
        s5 = Section5Data(
            stress_level=9,
            sleep_hours=5,
            smoking=True,
            cigarettes_per_day=20,
            diet_quality="buruk",
            exercise_frequency="tidak_pernah",
            health_conditions=["pcos", "sindrom_metabolik"],
        )
        bd = calculate_lifestyle_score(s5)
        assert bd.total_lifestyle_score > 60.0

    def test_healthy_lifestyle_low_score(self):
        s5 = Section5Data(
            stress_level=2,
            sleep_hours=8,
            smoking=False,
            diet_quality="sangat_baik",
            exercise_frequency="sedang",
        )
        bd = calculate_lifestyle_score(s5)
        assert bd.total_lifestyle_score < 25.0

    def test_lifestyle_score_bounded(self):
        s5 = Section5Data(
            stress_level=10,
            sleep_hours=4,
            smoking=True,
            cigarettes_per_day=40,
            diet_quality="buruk",
            exercise_frequency="tidak_pernah",
        )
        bd = calculate_lifestyle_score(s5)
        assert 0.0 <= bd.total_lifestyle_score <= 100.0

    def test_non_smoker_lower_than_smoker(self):
        base = dict(stress_level=5, sleep_hours=7, diet_quality="cukup",
                    exercise_frequency="ringan")
        bd_smoke = calculate_lifestyle_score(
            Section5Data(**base, smoking=True, cigarettes_per_day=20)
        )
        bd_clean = calculate_lifestyle_score(
            Section5Data(**base, smoking=False)
        )
        assert bd_smoke.total_lifestyle_score > bd_clean.total_lifestyle_score


# ── Hybrid risk calculation and categorisation tests ─────────────────────────

class TestHybridRiskCalculation:
    def _make_full_clinical(self, norwood=5, stress=8):
        s1 = Section1Data(age=28, gender="pria", ethnicity="Asia")
        s2 = Section2Data(
            hair_loss_per_day=200,
            loss_duration_months=24,
            loss_pattern="m-shape",
            thinning_areas=["hairline", "crown"],
            thinning_perception=8,
            diameter_decreased=True,
            norwood_scale=norwood,
        )
        s3 = Section3Data(hair_pull_count=15)
        s4 = Section4Data(
            maternal_grandfather_bald=True,
            father_bald=True,
            generations_bald=3,
        )
        s5 = Section5Data(
            stress_level=stress,
            sleep_hours=5,
            smoking=True,
            cigarettes_per_day=10,
        )
        return run_clinical_analysis(s1, s2, s3, s4, s5)

    def test_clinical_only_analysis_type(self):
        clinical = self._make_full_clinical()
        result = calculate_risk_score(None, clinical)
        assert result.analysis_type == "clinical_only"

    def test_clinical_only_score_nonzero(self):
        clinical = self._make_full_clinical()
        result = calculate_risk_score(None, clinical)
        assert result.hybrid_score >= 40.0

    def test_hybrid_analysis_type_when_genetic_provided(self):
        clinical = self._make_full_clinical()
        fasta = ">test\n" + "CAG" * 17 + "NNNNN" + "GGC" * 23
        genetic = run_genetic_analysis(
            fasta_text=fasta,
            snp_genotypes=HIGH_RISK_SNP,
        )
        result = calculate_risk_score(genetic, clinical)
        assert result.analysis_type == "hybrid"

    def test_hybrid_genetic_score_positive(self):
        clinical = self._make_full_clinical()
        fasta = ">test\n" + "CAG" * 17 + "NNNNN" + "GGC" * 23
        genetic = run_genetic_analysis(
            fasta_text=fasta,
            snp_genotypes=HIGH_RISK_SNP,
        )
        result = calculate_risk_score(genetic, clinical)
        assert result.genetic_score > 0

    def test_hybrid_score_bounded(self):
        clinical = self._make_full_clinical()
        fasta = ">test\n" + "CAG" * 17 + "NNNNN" + "GGC" * 23
        genetic = run_genetic_analysis(fasta_text=fasta, snp_genotypes=HIGH_RISK_SNP)
        result = calculate_risk_score(genetic, clinical)
        assert 0.0 <= result.hybrid_score <= 100.0

    def test_category_minimal(self):
        cat, color, desc = get_risk_category(10)
        assert cat == "MINIMAL"

    def test_category_rendah(self):
        cat, _, _ = get_risk_category(30)
        assert cat == "RENDAH"

    def test_category_sedang(self):
        cat, _, _ = get_risk_category(50)
        assert cat == "SEDANG"

    def test_category_tinggi(self):
        cat, _, _ = get_risk_category(70)
        assert cat == "TINGGI"

    def test_category_sangat_tinggi(self):
        cat, _, _ = get_risk_category(90)
        assert cat == "SANGAT_TINGGI"

    def test_category_returns_three_tuple(self):
        result = get_risk_category(50)
        assert len(result) == 3

    def test_risk_result_has_hybrid_score(self):
        clinical = self._make_full_clinical()
        result = calculate_risk_score(None, clinical)
        assert hasattr(result, "hybrid_score")


# ── FASTA and TSV parsing tests ───────────────────────────────────────────────

class TestParsing:
    def test_parse_fasta_basic(self):
        fasta = ">header\nATCGATCG\n"
        seq = parse_fasta(fasta)
        assert seq == "ATCGATCG"

    def test_parse_fasta_multiline(self):
        fasta = ">header\nATCG\nATCG\nATCG\n"
        seq = parse_fasta(fasta)
        assert seq == "ATCGATCGATCG"

    def test_parse_fasta_lowercase_normalised(self):
        fasta = ">header\natcgatcg\n"
        seq = parse_fasta(fasta)
        assert seq == "ATCGATCG"

    def test_parse_fasta_strips_non_nucleotides(self):
        fasta = ">header\nATCG1234ATCG\n"
        seq = parse_fasta(fasta)
        assert "1" not in seq and "2" not in seq

    def test_parse_fasta_empty_returns_empty(self):
        assert parse_fasta("") == ""

    def test_parse_tsv_basic(self):
        tsv = "rs6152\tG\nrs1385699\tC\n"
        genotypes = parse_tsv_genotypes(tsv)
        assert genotypes["rs6152"] == "G"
        assert genotypes["rs1385699"] == "C"

    def test_parse_tsv_with_hash_comments_skipped(self):
        tsv = "# comment\nrs6152\tG\n"
        genotypes = parse_tsv_genotypes(tsv)
        assert "rs6152" in genotypes
        assert len(genotypes) == 1

    def test_parse_tsv_empty_returns_empty_dict(self):
        genotypes = parse_tsv_genotypes("")
        assert genotypes == {}

    def test_run_genetic_analysis_fasta_cag_count(self):
        fasta = ">test\n" + "CAG" * 17 + "NNNNN" + "GGC" * 23
        result = run_genetic_analysis(fasta_text=fasta)
        assert result.has_sequence_data is True
        assert result.cag_result.count == 17

    def test_run_genetic_analysis_fasta_ggn_count(self):
        fasta = ">test\n" + "CAG" * 17 + "NNNNN" + "GGC" * 23
        result = run_genetic_analysis(fasta_text=fasta)
        assert result.ggn_result.count == 23

    def test_run_genetic_analysis_snp_only(self):
        result = run_genetic_analysis(snp_genotypes=HIGH_RISK_SNP)
        assert result.has_snp_data is True
        assert result.genetic_score > 50

    def test_run_genetic_analysis_no_input(self):
        result = run_genetic_analysis()
        assert result.has_sequence_data is False
        assert result.has_snp_data is False

    def test_run_genetic_analysis_genetic_score_bounded(self):
        fasta = ">test\n" + "CAG" * 17 + "NNNNN" + "GGC" * 23
        result = run_genetic_analysis(fasta_text=fasta, snp_genotypes=HIGH_RISK_SNP)
        assert 0.0 <= result.genetic_score <= 100.0
