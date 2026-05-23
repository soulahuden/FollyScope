# Folliscope, Methodology & Limitations

> **TL;DR.** Folliscope is an **educational decision-support tool**, not a clinical diagnostic.
> The *direction* of every risk factor it models is grounded in peer-reviewed literature.
> The *exact numerical score* is indicative, not a calibrated probability. The tool has
> **not been validated on a real patient cohort**, that would require ethics-board approval,
> a labeled outcome dataset, and external replication.
> Treat the score as a compass, not a GPS.

---

## 1. Scoring philosophy

Folliscope produces a single 0-100 risk score by combining four sub-scores:

| Mode | Formula |
|---|---|
| Hybrid (with DNA) | `0.45·Genetic + 0.30·Clinical + 0.15·Family + 0.10·Lifestyle`, × age modifier |
| Clinical-only     | `0.55·Clinical + 0.30·Family + 0.15·Lifestyle`, × age modifier |

`GeneticScore` itself is a weighted sum: `0.40·CAGScore + 0.15·GGNScore + 0.45·SNPScore`.

Each sub-score is bounded 0-100. The **age modifier** is a small multiplier (×1.00-1.15)
that weights early-onset symptoms more heavily, reflecting the clinical observation that
AGA presenting before age 30 generally indicates higher AR sensitivity.

---

## 2. What is empirically grounded vs. designed

This section is the most important one, the project is honest about which parts of the
model rest on literature and which are pragmatic design choices that future work would
need to calibrate.

### ✅ Validated by peer-reviewed literature

| Component | Source / consensus |
|---|---|
| **CAG repeat → AR sensitivity** | 30+ years of consensus, from Choong et al. 1996 onward. Shorter CAG → stronger transcriptional activation → more DHT-responsive follicles. |
| **GGN repeat secondary effect** | Hillmer et al. 2005; secondary modifier, weaker than CAG. |
| **9 SNP panel, with Odds Ratios** | Each SNP and its OR taken from a GWAS or meta-analysis publication. See `frontend/about.html` for full citation list and `backend/reference_data.py` for the per-SNP source. |
| **Norwood / Ludwig clinical staging** | Norwood 1975 / Ludwig 1977, the de-facto clinical scales used in dermatology since publication. |
| **X-linked inheritance pattern** | Standard genetics. Sons inherit X from mother → mother inherited it from her father. Hence maternal grandfather is the strongest single family-history predictor, and brothers (sharing the same maternal X distribution) cluster. |
| **Individual lifestyle factors** | Smoking → vasoconstriction → reduced follicle perfusion (Su & Chen 2007); chronic stress → cortisol → catagen entry (Peters et al. 2017); micronutrient status (iron, vitamin D, biotin) influences hair-cycle dynamics. |

### ⚠️ Design choices (NOT empirically calibrated)

| Component | Status |
|---|---|
| **Hybrid weights (0.45 / 0.30 / 0.15 / 0.10)** | Chosen by hand based on relative confidence in each signal source. **Not learned from regression on labeled cohort data.** |
| **Clinical-only weights (0.55 / 0.30 / 0.15)** | Same, re-normalized when genetic data is absent. |
| **`GeneticScore` sub-weights (0.40 / 0.15 / 0.45)** | Chosen to reflect CAG = strongest single locus, GGN = secondary, SNP panel = aggregate signal. Not regressed. |
| **`ClinicalScore` sub-component weights** (Norwood 35%, pattern-area 20%, hair-pull 15%, etc.) | Designed, not learned. |
| **Age modifier (×1.00 / ×1.08 / ×1.15)** | Estimates, not from a clinical cohort. |
| **Risk category cut-offs** (0-19 Minimal, 20-39 Low, … 80-100 Very High) | Designed to spread the score visually across the gauge. Not validated against patient outcomes. |
| **Confidence percentages** (70% / 85% / 95%) | Indicative of *which inputs* were used, **not** calibrated probabilities. They are not Bayesian posteriors. |

### 🔬 Phenotype-to-genotype inference (`backend/phenotype_inference.py`)

When the user has no DNA data, the tool estimates a *probable* AR CAG-repeat range from
clinical signals. The method is:

```
shift = 4.0 · norwood_severity + 3.5 · family_pressure + 2.5 · early_onset_signal
estimated_CAG = 22 − shift,  clamped to [12, 40]
```

The directional logic is defensible (severe symptoms + maternal-grandfather signal +
early onset all correlate with shorter CAG in the literature), but the **coefficients
(4.0, 3.5, 2.5) and the base of 22 are educated guesses**, not regression-fit values.

Output confidence is deliberately reported as **low** or **medium**, never high, to
make this honest to the user.

---

## 3. What Folliscope is NOT

- **Not a clinical diagnostic.** Folliscope cannot diagnose AGA or rule it out.
- **Not personalized medicine.** Two users with identical scores may have very different
  underlying biology, pharmacogenomic response varies.
- **Not a substitute for trichoscopy.** A dermatologist examining the scalp with a
  trichoscope sees follicle miniaturization directly; we infer it from a questionnaire.
- **Not validated cross-population.** CAG-length thresholds (the 18 / 22 / 25 / 30 cuts)
  were established largely in Caucasian European cohorts. Asian and African
  distributions are partially documented but the thresholds may shift, and the OR values
  for the 9-SNP panel are similarly population-dependent. **A user from a population
  under-represented in the source studies should treat the result with extra caution.**
- **Not exhaustive of AGA genetics.** Recent GWAS meta-analyses have mapped 200+ loci
  associated with AGA. Folliscope uses 9 of the most replicated, useful for education,
  but a research-grade PRS would draw on millions of variants.

---

## 4. What would be needed to validate

For Folliscope to graduate from "educational tool" to "calibrated predictor", the
following would be required:

1. **A labeled cohort.** ≥1,000 individuals with measured AR CAG repeats, SNP genotypes,
   completed clinical questionnaire, and a clinician-confirmed Norwood/Ludwig stage at
   follow-up. Ethics-board approval required.
2. **Held-out test split.** Train weights on one subset, evaluate on a different subset
   that the model never saw.
3. **Calibration analysis.** Predicted "70% confidence" must correspond to ~70%
   observed accuracy on held-out data.
4. **External replication.** A second cohort, ideally from a different population,
   confirms the trained weights generalize.
5. **Comparison against a clinical baseline.** Is Folliscope better than a dermatologist
   reading Norwood stage alone? Better than family history alone?

None of those steps have been completed. Folliscope's current design is honest about
this and reports confidence levels accordingly.

---

## 5. Reproducibility

- All scoring logic lives in `backend/risk_score.py`, `backend/clinical_analyzer.py`,
  and `backend/analyzer.py`. Functions are pure and unit-tested.
- 66 unit tests in `tests/test_folliscope.py` cover CAG/GGN counting, SNP detection,
  per-component scoring, hybrid integration, and parsing edge cases.
- Sample data in `sample_data/` (synthetic, not real patient data) is included so that
  any reviewer can re-run the pipeline end-to-end.
- The exact NCBI reference used as the comparison baseline is
  [NM_000044.6](https://www.ncbi.nlm.nih.gov/nuccore/NM_000044.6), fetched live via
  the Entrez API.

---

## 6. Key references

- Choong CS, Kemppainen JA, Zhou ZX, Wilson EM. (1996). *Reduced androgen receptor gene expression with first exon CAG repeat expansion.* Mol Endocrinol 10(12):1527-35.
- Hillmer AM, Hanneken S, Ritzmann S, et al. (2005). *Genetic variation in the human androgen receptor gene is the major determinant of common early-onset androgenetic alopecia.* Am J Hum Genet 77(1):140-8.
- Heilmann-Heimbach S, Herold C, Hochfeld LM, et al. (2017). *Meta-analysis identifies novel risk loci and yields systematic insights into the biology of male-pattern baldness.* Nat Commun 8:14694.
- Ellis JA, Stebbing M, Harrap SB. (2001). *Polymorphism of the androgen receptor gene is associated with male pattern baldness.* J Invest Dermatol 116(3):452-5.
- Prodi DA, Pirastu N, Maninchedda G, et al. (2008). *EDA2R is associated with androgenetic alopecia.* J Invest Dermatol 128(9):2268-70.
- Norwood OT. (1975). *Male pattern baldness: classification and incidence.* South Med J 68(11):1359-65.
- Ludwig E. (1977). *Classification of the types of androgenetic alopecia (common baldness) occurring in the female sex.* Br J Dermatol 97(3):247-54.
- Peters EMJ, Müller Y, Snaga W, et al. (2017). *Hair and stress: a pilot study of hair and cytokine balance alteration in healthy young women under major exam stress.* PLoS ONE 12(4):e0175904.
- Su LH, Chen TH. (2007). *Association of androgenetic alopecia with smoking and its prevalence among Asian men.* Arch Dermatol 143(11):1401-6.

A full list with PubMed links is available on the [Science page](frontend/about.html#references).
