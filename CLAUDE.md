# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## About

**BaldGuard** is an educational computational biology project — an early-warning androgenetic alopecia (AGA/baldness) risk system. It combines genetic analysis (CAG/GGN repeat counting, SNP panel) with a clinical questionnaire to produce a hybrid polygenic risk score (PRS). It is **not** a clinical diagnostic tool.

## Commands

### Run the server

```bash
# Development (auto-reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or directly:
python main.py
```

The frontend is served at `http://localhost:8000`.

### Run tests

```bash
# All tests (66 test cases)
pytest tests/ -v

# Single test class
pytest tests/test_baldguard.py::TestCAGRepeats -v
pytest tests/test_baldguard.py::TestHybridRiskCalculation -v

# Single test
pytest tests/test_baldguard.py::TestCAGRepeats::test_cag_17_count -v
```

### Install dependencies

```bash
pip install -r requirements.txt
```

Key packages: `fastapi`, `uvicorn[standard]`, `pydantic==2.7.1`, `biopython`, `pytest`, `httpx`.

## Architecture

### Data Flow

```
FASTA sequence  ──► analyzer.py (parse_fasta → count_cag_repeats / count_ggn_repeats)
                         │
SNP dict        ──► analyzer.py (analyze_snps → calculate_snp_score)
                         │
                    calculate_genetic_score()  ──► GeneticAnalysisResult
                                                         │
Clinical form   ──► clinical_analyzer.py (run_clinical_analysis) ──► ClinicalAnalysisResult
(5 sections)         (clinical_score + family_score + lifestyle_score + age_modifier)
                                                         │
                    risk_score.py (calculate_risk_score) ──► RiskScoreResult
                         │
                    api.py → JSON response
```

### Module Responsibilities

| Module | Role |
|--------|------|
| `backend/reference_data.py` | All static data: `SNP_DATABASE` (9 SNPRecords), `CAG_THRESHOLDS`, `GGN_THRESHOLDS`, `RISK_CATEGORIES`, `RECOMMENDATIONS` |
| `backend/analyzer.py` | Regex-based CAG/GGN repeat counting; SNP comparison; genetic score calculation; FASTA + TSV parsing |
| `backend/clinical_analyzer.py` | Scores the 5-section clinical questionnaire (Norwood/Ludwig scale, hair pull test, family history weighting, lifestyle factors) |
| `backend/risk_score.py` | Hybrid PRS formula: `0.45×Genetic + 0.30×Clinical + 0.15×Family + 0.10×Lifestyle` × age modifier; falls back to `clinical_only` mode when no genetic data |
| `backend/api.py` | FastAPI router (`/api/...`); Pydantic v2 request/response models; main `/api/analyze` endpoint |
| `main.py` | FastAPI app entry point; serves HTML pages at `/`, `/analyze`, `/about`, `/database`; mounts `sample_data/` at `/sample_data/`; mounts `frontend/` at `/` as catch-all (CSS, JS, `.html` direct access) |
| `frontend/js/api.js` | Browser-side HTTP client calling the backend REST API |
| `frontend/js/main.js` | Multi-step wizard UI controller; form state management |
| `frontend/js/charts.js` | Chart.js visualizations (radar, bar, SNP heatmap) |

### Risk Score Formula

**Hybrid mode** (when genetic data is provided):
```
HybridScore = (0.45 × GeneticScore + 0.30 × ClinicalScore + 0.15 × FamilyScore + 0.10 × LifestyleScore) × age_modifier
```

**Clinical-only mode** (no genetic data):
```
ClinicalOnlyScore = (0.55 × ClinicalScore + 0.30 × FamilyScore + 0.15 × LifestyleScore) × age_modifier
```

**GeneticScore** = `0.40 × CAGScore + 0.15 × GGNScore + 0.45 × SNPScore`

### CAG Repeat Risk Thresholds (Choong 1996)

| CAG Count | Risk Level |
|-----------|------------|
| < 18 | SANGAT_TINGGI (score 100) |
| 18–21 | TINGGI (score 80) |
| 22–24 | SEDANG (score 60) |
| 25–29 | RENDAH (score 35) |
| ≥ 30 | PROTEKTIF (score 10) |

### Extending the System

- **Add a new SNP:** Add a `SNPRecord` to `SNP_DATABASE` in `backend/reference_data.py`, then update `frontend/database.html`.
- **Change CAG/GGN thresholds:** Edit `CAG_THRESHOLDS` / `GGN_THRESHOLDS` in `backend/reference_data.py`.
- **Change formula weights:** Edit `calculate_hybrid_score()` or `calculate_clinical_only_score()` in `backend/risk_score.py`.
- **Change recommendations:** Edit the `RECOMMENDATIONS` dict in `backend/reference_data.py`.

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/snp-database` | Full SNP reference table |
| POST | `/api/analyze` | Main hybrid/clinical analysis |
| POST | `/api/analyze/fasta-upload` | Upload FASTA file, returns CAG/GGN counts |

### Sample Data

`sample_data/` contains pre-built FASTA + TSV pairs for testing without real genomic data:
- `high_risk_*` — CAG=17, GGN=23, all 9 SNPs as risk alleles
- `medium_risk_*` — CAG=23, GGN=22, 5 SNPs as risk alleles
- `low_risk_*` — CAG=29, GGN=20, 2 SNPs as risk alleles
- `protective_sample.fasta` — CAG=33, GGN=18 (no TSV needed)
