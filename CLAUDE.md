# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## About

**Folliscope** is an educational computational biology project, an early-warning androgenetic alopecia (AGA/baldness) risk system. It combines genetic analysis (CAG/GGN repeat counting, SNP panel) with a clinical questionnaire to produce a hybrid polygenic risk score (PRS). It is **not** a clinical diagnostic tool.

The system supports three input modes:
- **Genetic-only:** CAG/GGN repeats + SNP panel from FASTA/TSV/23andMe raw data
- **Clinical-only:** 5-section questionnaire (no genetic data required)
- **Hybrid:** Combines genetic + clinical + family history + lifestyle factors

## Commands

### Quick start (Docker, recommended)

```bash
docker compose up --build    # First time, or after code changes
docker compose up            # Subsequent runs
docker compose down          # Stop
```

Visit `http://localhost:8000`

### Manual development setup

```bash
# Install dependencies
pip install -r requirements.txt

# Development server (auto-reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or directly
python main.py
```

Frontend is served at `http://localhost:8000`.

### Run tests

```bash
# All tests (66 cases across 9 test classes)
pytest tests/ -v

# Test categories
pytest tests/test_folliscope.py::TestCAGRepeats -v          # CAG repeat counting
pytest tests/test_folliscope.py::TestGGNRepeats -v          # GGN repeat counting
pytest tests/test_folliscope.py::TestSNPDetection -v        # SNP scoring
pytest tests/test_folliscope.py::TestClinicalScore -v       # Clinical questionnaire
pytest tests/test_folliscope.py::TestFamilyScore -v         # Family history weighting
pytest tests/test_folliscope.py::TestLifestyleScore -v      # Lifestyle factors
pytest tests/test_folliscope.py::TestHybridRiskCalculation -v  # PRS formula
pytest tests/test_folliscope.py::TestParsing -v             # FASTA/TSV parsing

# Single test
pytest tests/test_folliscope.py::TestCAGRepeats::test_cag_17_count -v
```

## Architecture

### Data Flow

```
FASTA sequence  ──► analyzer.py (count_cag_repeats / count_ggn_repeats)
                         │
SNP dict        ──► analyzer.py (analyze_snps → calculate_snp_score)
(TSV/23andMe)            │
                         ▼
                  calculate_genetic_score() ──► GeneticAnalysisResult
                         │
                         │◄─── backend/ncbi.py (fetch AR reference)
                         │
Clinical form   ──► clinical_analyzer.py (5 sections + scoring logic)
(5 sections)             │
                         ├── clinical_score (Norwood/Ludwig/hair pull/etc)
                         ├── family_score (X-linked family history)
                         ├── lifestyle_score (stres/tidur/merokok/dll)
                         └── age_modifier
                         │
              ┌──────────┴──────────────────────────────┐
              │                                         │
    (has genetic data)               (no genetic data)
              │                                         │
              ▼                                         ▼
    risk_score.py              phenotype_inference.py
  (hybrid formula)              (infer CAG range)
              │                          │
              └──────────┬───────────────┘
                         ▼
   ┌───────────────────────────────────────┐
   │  AnalysisConfidence                  │
   │  + NCBI comparison narrative         │
   └───────────────────────────────────────┘
              ▼
  ┌──────────────────────┐
  │  HybridScore or      │
  │  ClinicalOnlyScore   │
  └──────────────────────┘
              ▼
       api.py → JSON response
```

### Module Responsibilities

| Module | Role |
|--------|------|
| `main.py` | FastAPI app entry point; serves HTML pages at `/`, `/analyze`, `/about`, `/database` (clean routes); mounts `/sample_data/` and `/` catch-all for static files (CSS, JS) |
| `backend/api.py` | FastAPI router (`/api/...`); Pydantic v2 request/response models; main `/api/analyze` endpoint; health check |
| `backend/reference_data.py` | Static data: `SNP_DATABASE` (9 SNPRecords), `CAG_THRESHOLDS`, `GGN_THRESHOLDS`, `RISK_CATEGORIES`, `RECOMMENDATIONS` |
| `backend/analyzer.py` | Regex-based CAG/GGN repeat counting; SNP comparison; genetic score calculation; FASTA + TSV parsing; dosage calculation for diploid genotypes |
| `backend/clinical_analyzer.py` | Scores 5-section clinical questionnaire: clinical (Norwood/Ludwig), family history, lifestyle, age modifier; returns `ClinicalAnalysisResult` |
| `backend/risk_score.py` | Hybrid PRS formula: `0.45×Genetic + 0.30×Clinical + 0.15×Family + 0.10×Lifestyle` × age_modifier; falls back to `clinical_only` mode when no genetic data |
| `backend/ncbi.py` | NCBI Entrez integration: fetches AR reference sequence (NM_000044.6) for baseline CAG/GGN count comparison |
| `backend/parser_23andme.py` | Parses 23andMe raw data files (.txt); extracts genotypes for the 9 SNPs in `SNP_DATABASE` |
| `backend/phenotype_inference.py` | Infers probable AR CAG-repeat range from clinical signals alone (when no DNA data provided); returns `PhenotypeInference` with confidence level; includes `AnalysisConfidence` & NCBI comparison builder |
| `frontend/` | HTML/CSS/JS: `index.html` (landing), `analyze.html` (wizard form), `about.html` (scientific explanation), `database.html` (SNP reference table) |
| `frontend/js/api.js` | Browser HTTP client; calls `/api/analyze`, `/api/fasta-upload`, `/api/snp-database` |
| `frontend/js/main.js` | Multi-step form wizard; state management; form validation; navigation between clinical/genetic/results tabs |
| `frontend/js/charts.js` | Chart.js visualizations: radar (score components), bar (risk categories), SNP heatmap |

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

### Phenotype Inference & Confidence System

When no DNA sequence is provided, **phenotype_inference.py** estimates a probable CAG-repeat range from clinical signals:
- Weighted combination of Norwood/Ludwig severity, family history (especially maternal grandfather), and early-onset signals
- Estimates range (min-max) + midpoint, mapped to risk bands (PROTECTIVE → VERY_HIGH)
- Returns explicit confidence level: **low** (limited signals) → **medium** (strong corroborating evidence)
- Always displays NCBI reference (NM_000044.6, ~22 CAG) for educational context

**Analysis confidence** is reported to the user via `AnalysisConfidence` dataclass:
- **Questionnaire only** (70% confidence): No genetic data provided
- **Questionnaire + SNP panel** (85% confidence): SNP genotypes add measured signal
- **Questionnaire + DNA sequence** (95% confidence): Measured CAG/GGN repeats from FASTA

This enables users without DNA data to still receive an interpretable, science-grounded risk narrative.

### CAG Repeat Risk Thresholds (Choong 1996)

| CAG Count | Risk Level | Score |
|-----------|------------|-------|
| < 18 | SANGAT_TINGGI | 100 |
| 18-21 | TINGGI | 80 |
| 22-24 | SEDANG | 60 |
| 25-29 | RENDAH | 30 |
| ≥ 30 | PROTEKTIF | 10 |

### Validation Status & Design Decisions

**Validated (from peer-reviewed literature):**
- CAG repeat thresholds and mechanism (30+ years of consensus)
- 9 SNPs and their Odds Ratios (from GWAS studies)
- Skala Norwood (pria) / Ludwig (wanita), clinical standard
- X-linked inheritance logic (family history weighting)
- Individual risk factors (stres → kortisol, merokok → vasokonstriksi, etc.)

**Design choices (not empirically validated):**
- Hybrid formula weights (0.45, 0.30, 0.15, 0.10), chosen manually, not from regression on patient data
- Age modifiers (1.15×, 1.08×, etc.), estimates, not from clinical cohort
- Sub-component weights within ClinicalScore (e.g., Norwood = 35%, hair pull = 15%), manual design
- Risk category cut-offs (0-19, 20-39, 40-59, etc.), not validated against real patient outcomes

**Key limitation:** Folliscope acts like a **compass** (shows direction) not a **GPS** (precise prediction). The direction and type of risk factors are scientifically sound. The exact numerical score is **indidicative, not clinical prediction**.

### Important Notes

- **Pydantic v2:** Pinned at `pydantic==2.7.1`. Uses `BaseModel` and `Field` validators. Non-backward-compatible with v1 (no `.parse_obj()`, uses model constructors instead).
- **Frontend static file mounting:** Routes must be registered in order:
  1. API routes (`/api/*`)
  2. Explicit HTML routes (`/`, `/analyze`, `/about`, `/database`)
  3. Static mounts, `/sample_data/` then `/` (catch-all)
  
  Mounting `/` last ensures it doesn't shadow earlier routes.

- **CORS enabled:** `allow_origins=["*"]` for development. Change if deployed behind strict firewall.

### Extending the System

- **Add a new SNP:** Add `SNPRecord` to `SNP_DATABASE` in `backend/reference_data.py`, then update `frontend/database.html` to display it.
- **Change CAG/GGN thresholds:** Edit `CAG_THRESHOLDS` / `GGN_THRESHOLDS` in `backend/reference_data.py`.
- **Change formula weights:** Edit `calculate_hybrid_score()` or `calculate_clinical_only_score()` in `backend/risk_score.py`.
- **Change recommendations:** Edit `RECOMMENDATIONS` dict in `backend/reference_data.py`.

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check: `{"status":"ok","service":"Folliscope API","timestamp":"..."}` |
| GET | `/api/snp-database` | Returns all 9 SNPs with OR, weights, and descriptions |
| POST | `/api/analyze` | Main endpoint: accepts genetic_data + 5 clinical sections; returns hybrid/clinical score |
| POST | `/api/analyze/fasta-upload` | Upload FASTA; returns detected CAG/GGN counts |

### Sample Data

`sample_data/` contains synthetic test data (not real patient data):

- `high_risk_sample.fasta`, CAG=17, GGN=23 (demonstrating high risk)
- `medium_risk_sample.fasta`, CAG=23, GGN=22
- `low_risk_sample.fasta`, CAG=29, GGN=20
- `protective_sample.fasta`, CAG=33, GGN=18
- `*_genotype.tsv`, TSV files with alleles for each SNP

Used by `sample_data/` button in the web UI for quick testing.
