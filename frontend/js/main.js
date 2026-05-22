// main.js — BaldGuard front-end integration
// Collects questionnaire data, calls /api/analyze, and renders the
// risk profile, NCBI comparison, confidence indicator, and phenotype
// inference returned by the backend.
// Exposed via window.BaldGuardMain.processResults(withGenetic).

(function () {
  'use strict';

  // ── Form data collection ────────────────────────────────────────────────

  function getVal(id)     { const el = document.getElementById(id); return el ? el.value : null; }
  function getNum(id)     { const v = parseInt(getVal(id), 10); return isNaN(v) ? null : v; }
  function getFloat(id)   { const v = parseFloat(getVal(id));    return isNaN(v) ? null : v; }
  function getChecked(id) { const el = document.getElementById(id); return el ? el.checked : false; }
  function getRadio(name) { const el = document.querySelector(`input[name="${name}"]:checked`); return el ? el.value : null; }
  function getCheckboxList(name) {
    return Array.from(document.querySelectorAll(`input[name="${name}"]:checked`))
      .map(e => e.value)
      .filter(v => v && v !== 'none');
  }

  function collectFormData() {
    const gender = getRadio('gender') || 'male';

    const section1 = {
      age:          getNum('age') || 30,
      gender:       gender,                          // backend accepts 'male' / 'female' too
      ethnicity:    getVal('ethnicity') || 'Asia',
      puberty_age:  getNum('puberty_age'),
    };

    let norwoodScale = null;
    let ludwigScale  = null;
    if (gender === 'male') {
      const nw = getRadio('norwood_scale');
      norwoodScale = nw ? parseInt(nw, 10) : null;
    } else {
      const lw = getRadio('ludwig_scale');
      ludwigScale = lw ? parseInt(lw, 10) : null;
    }

    const section2 = {
      hair_loss_per_day:     getNum('hair_loss') || 80,
      loss_duration_months:  getNum('duration_months') || 0,
      loss_pattern:          getRadio('loss_pattern') || 'none',
      thinning_areas:        getCheckboxList('thinning_area'),
      thinning_perception:   getNum('thinning_perception') || 1,
      diameter_decreased:    getChecked('diameter_decrease'),
      norwood_scale:         norwoodScale,
      ludwig_scale:          ludwigScale,
    };

    const section3 = { hair_pull_count: getNum('pull_test') };

    const fatherBald     = getRadio('father_bald') === 'yes';
    const maternalGfBald = getRadio('maternal_gf_bald') === 'yes';
    const paternalGfBald = getRadio('paternal_gf_bald') === 'yes';
    const brothersBald   = getRadio('brothers_bald') === 'yes';
    const motherThinning = getRadio('mother_thinning') === 'yes';
    const sistersRaw     = getRadio('sisters_thinning');

    const section4 = {
      father_bald:                    fatherBald,
      father_bald_age:                fatherBald ? getNum('father_bald_age') : null,
      maternal_grandfather_bald:      maternalGfBald,
      maternal_grandfather_bald_age:  maternalGfBald ? getNum('maternal_gf_bald_age') : null,
      paternal_grandfather_bald:      paternalGfBald,
      brothers_bald:                  brothersBald,
      mother_thinning:                motherThinning,
      generations_bald:               getNum('generations') || 0,
      sisters_thinning:               sistersRaw === 'yes' ? true : sistersRaw === 'no' ? false : null,
    };

    const section5 = {
      stress_level:          getNum('stress') || 5,
      sleep_hours:           getFloat('sleep') || 7.0,
      smoking:               getChecked('smoking'),
      cigarettes_per_day:    getChecked('smoking') ? (getNum('cigarettes_per_day') || 0) : 0,
      alcohol_frequency:     getVal('alcohol') || 'never',
      diet_quality:          getRadio('diet_quality') || 'balanced',
      exercise_frequency:    getRadio('exercise_frequency') || 'moderate',
      aggressive_styling:    getChecked('aggressive_styling'),
      medications:           getCheckboxList('medication'),
      health_conditions:     getCheckboxList('health_condition'),
      vitamin_deficiencies:  getCheckboxList('vitamin_deficiency'),
    };

    return { section1, section2, section3, section4, section5 };
  }

  function collectGeneticData() {
    const fastaText = (document.getElementById('fastaTextarea')?.value || '').trim();
    const snpGenotypes = {};

    if (window._23andmeGenotypes && Object.keys(window._23andmeGenotypes).length > 0) {
      Object.assign(snpGenotypes, window._23andmeGenotypes);
    }
    document.querySelectorAll('#snpTableBody select').forEach(sel => {
      const rsid = sel.name?.replace('snp_', '');
      if (rsid && sel.value && sel.value !== 'unknown') snpGenotypes[rsid] = sel.value;
    });

    const hasFasta = fastaText.length > 0;
    const hasSnp   = Object.keys(snpGenotypes).length > 0;
    if (!hasFasta && !hasSnp) return null;

    return {
      fasta_sequence: hasFasta ? fastaText : undefined,
      snp_genotypes:  hasSnp   ? snpGenotypes : undefined,
    };
  }

  // ── Label maps (backend returns Indonesian keys for risk band; we display English) ──

  const RISK_LABEL = {
    MINIMAL:       'Minimal',
    RENDAH:        'Low',
    SEDANG:        'Moderate',
    TINGGI:        'High',
    SANGAT_TINGGI: 'Very high',
  };

  const RISK_BAND_LABEL = {
    PROTECTIVE: 'Protective',
    LOW:        'Low sensitivity',
    MODERATE:   'Moderate sensitivity',
    HIGH:       'High sensitivity',
    VERY_HIGH:  'Very high sensitivity',
  };

  const ANALYSIS_TYPE_LABEL = {
    hybrid:        '<i class="fa-solid fa-dna"></i> Hybrid analysis · Questionnaire + DNA',
    clinical_only: '<i class="fa-solid fa-clipboard-list"></i> Questionnaire-based analysis',
    genetic_only:  '<i class="fa-solid fa-dna"></i> Genetic-only analysis',
  };

  // ── Result display ─────────────────────────────────────────────────────

  function applyResults(result) {
    const scores = result.scores;
    const color  = result.risk_color || '#f59e0b';

    // Gauge & headline score
    const gaugeMarker = document.getElementById('gaugeMarker');
    if (gaugeMarker) gaugeMarker.style.left = Math.min(scores.hybrid_score, 100) + '%';

    const scoreEl = document.getElementById('riskScore');
    if (scoreEl) { scoreEl.textContent = scores.hybrid_score.toFixed(1); scoreEl.style.color = color; }

    const catEl = document.getElementById('riskCategory');
    if (catEl) {
      catEl.textContent = (result.risk_category_label || RISK_LABEL[result.risk_category] || result.risk_category) + ' risk';
      catEl.style.background = color + '22';
      catEl.style.color = color;
    }

    const descEl = document.getElementById('riskDescription');
    if (descEl) descEl.textContent = result.risk_description || '';

    const badgeEl = document.getElementById('analysisTypeBadge');
    if (badgeEl) badgeEl.innerHTML = ANALYSIS_TYPE_LABEL[result.analysis_type] || result.analysis_type;

    // ── Confidence card ───────────────────────────────────────────────
    if (result.confidence) {
      const c = result.confidence;
      const pct  = document.getElementById('confidencePct');
      const fill = document.getElementById('confidenceFill');
      const desc = document.getElementById('confidenceDesc');
      const inp  = document.getElementById('confidenceInputs');
      if (pct)  pct.textContent = c.percent + '%';
      if (fill) fill.style.width = c.percent + '%';
      if (desc) desc.textContent = c.description;
      if (inp)  inp.innerHTML = (c.inputs_used || [])
                  .map(x => `<span class="badge badge--ink">${x}</span>`).join('');
    }

    // ── NCBI comparison card ──────────────────────────────────────────
    renderNcbiComparison(result.ncbi_comparison);

    // ── Score cards (component breakdown) ─────────────────────────────
    function setCard(valId, barId, score, notApplicable) {
      const val = document.getElementById(valId);
      const bar = document.getElementById(barId);
      if (val) val.textContent = notApplicable ? 'N/A' : score.toFixed(1);
      if (bar) bar.style.width = notApplicable ? '0%' : Math.min(score, 100) + '%';
    }
    const hasGeneticData = result.analysis_type === 'hybrid' || result.analysis_type === 'genetic_only';
    setCard('geneticScoreVal',   'geneticScoreBar',   scores.genetic_score,   !hasGeneticData);
    setCard('clinicalScoreVal',  'clinicalScoreBar',  scores.clinical_score,  false);
    setCard('familyScoreVal',    'familyScoreBar',    scores.family_score,    false);
    setCard('lifestyleScoreVal', 'lifestyleScoreBar', scores.lifestyle_score, false);

    // SNP / genetic detail visibility
    const snpCard = document.getElementById('snpHeatmapCard');
    const genCard = document.getElementById('geneticDetailCard');
    if (snpCard) snpCard.style.display = hasGeneticData ? 'block' : 'none';
    if (genCard) genCard.style.display = hasGeneticData ? 'block' : 'none';

    // ── Recommendations ───────────────────────────────────────────────
    const recList = document.getElementById('recommendationsList');
    if (recList && Array.isArray(result.recommendations)) {
      const icons = ['fa-user-doctor', 'fa-moon', 'fa-apple-whole', 'fa-spa',
                     'fa-scissors', 'fa-vial', 'fa-pills', 'fa-heart-pulse'];
      recList.innerHTML = result.recommendations.map((rec, i) => `
        <li class="rec-item">
          <span class="ric"><i class="fa-solid ${icons[i % icons.length]}"></i></span>
          <p>${rec}</p>
        </li>`).join('');
    }

    // ── Collapsible breakdown panels ──────────────────────────────────
    renderClinicalDetail(result.clinical_details);
    renderFamilyDetail(result.clinical_details);
    renderLifestyleDetail(result.clinical_details);
    if (hasGeneticData && result.genetic_details) {
      renderGeneticDetail(result.genetic_details);
    }
  }

  // ── NCBI comparison rendering ─────────────────────────────────────────

  function renderNcbiComparison(cmp) {
    if (!cmp) return;
    const axis = document.getElementById('cagAxis');
    const ncbiCagVal     = document.getElementById('ncbiCagVal');
    const userCagVal     = document.getElementById('userCagVal');
    const userValueLabel = document.getElementById('userValueLabel');
    const accession      = document.getElementById('ncbiAccession');
    const interp         = document.getElementById('compareInterpretation');
    const reasoningList  = document.getElementById('reasoningList');

    if (accession)  accession.textContent  = cmp.ncbi_accession || 'NM_000044.6';
    if (ncbiCagVal) ncbiCagVal.textContent = cmp.ncbi_reference_cag;
    if (userValueLabel) userValueLabel.textContent = cmp.user_value_type === 'measured' ? 'measured' : 'estimated';

    const userMin = cmp.user_cag_min;
    const userMax = cmp.user_cag_max;
    const userMid = cmp.user_cag_midpoint;
    if (userCagVal) {
      userCagVal.textContent = (cmp.user_value_type === 'measured' || userMin === userMax)
        ? String(userMid)
        : `${userMin}–${userMax}`;
    }

    // Axis: 10..40 CAG → 0..100% width
    const AXIS_MIN = 10, AXIS_MAX = 40;
    const pct = (v) => Math.max(0, Math.min(100, ((v - AXIS_MIN) / (AXIS_MAX - AXIS_MIN)) * 100));

    if (axis) {
      axis.innerHTML = '';
      // user range band (only if range, not single measurement)
      if (userMin !== userMax) {
        const range = document.createElement('div');
        range.className = 'cag-range';
        range.style.left  = pct(userMin) + '%';
        range.style.width = (pct(userMax) - pct(userMin)) + '%';
        axis.appendChild(range);
      }
      // user midpoint marker
      const userMarker = document.createElement('div');
      userMarker.className = 'cag-marker user';
      userMarker.style.left = pct(userMid) + '%';
      userMarker.innerHTML = `<div class="dot"></div><div class="label">You · ${userMid}</div>`;
      axis.appendChild(userMarker);

      // NCBI reference marker
      const ncbiMarker = document.createElement('div');
      ncbiMarker.className = 'cag-marker ncbi';
      ncbiMarker.style.left = pct(cmp.ncbi_reference_cag) + '%';
      ncbiMarker.innerHTML = `<div class="dot"></div><div class="label">NCBI · ${cmp.ncbi_reference_cag}</div>`;
      axis.appendChild(ncbiMarker);
    }

    if (interp) interp.textContent = cmp.interpretation || '';

    if (reasoningList) {
      const reasons = cmp.inference_reasoning || [];
      reasoningList.innerHTML = reasons.map(r => `<li>${r}</li>`).join('');
    }
  }

  // ── Detail panels ─────────────────────────────────────────────────────

  function row(label, value) {
    return `<div class="detail-row"><span>${label}</span><strong>${value}</strong></div>`;
  }

  function renderClinicalDetail(cd) {
    const el = document.getElementById('detailClinical');
    if (!el || !cd) return;
    el.innerHTML = `<div class="detail-grid">
      ${row('Norwood / Ludwig stage',    cd.norwood_ludwig_score.toFixed(0)  + ' / 100')}
      ${row('Pattern & affected area',    cd.pattern_area_score.toFixed(0)    + ' / 100')}
      ${row('Hair-pull test',             cd.hair_pull_score.toFixed(0)       + ' / 100')}
      ${row('Daily shedding volume',      cd.loss_volume_score.toFixed(0)     + ' / 100')}
      ${row('Hair miniaturization',       cd.miniaturization_score.toFixed(0) + ' / 100')}
      ${row('Symptom duration',           cd.duration_score.toFixed(0)        + ' / 100')}
      ${row('Age modifier',               (cd.age_modifier || 1).toFixed(2)   + '×')}
    </div>`;
  }

  function renderFamilyDetail(cd) {
    const el = document.getElementById('detailFamily');
    if (!el || !cd || !cd.family_breakdown) return;
    const fb = cd.family_breakdown;
    el.innerHTML = `<div class="detail-grid">
      ${row('Maternal grandfather · X-linked', fb.maternal_grandfather.toFixed(0) + ' / 100')}
      ${row('Father',                          fb.father.toFixed(0)               + ' / 100')}
      ${row('Paternal grandfather',            fb.paternal_grandfather.toFixed(0) + ' / 100')}
      ${row('Brothers',                        fb.brothers.toFixed(0)             + ' / 100')}
      ${row('Mother',                          fb.mother.toFixed(0)               + ' / 100')}
      ${row('Generations affected',            fb.generations.toFixed(0)          + ' / 100')}
    </div>`;
  }

  function renderLifestyleDetail(cd) {
    const el = document.getElementById('detailLifestyle');
    if (!el || !cd || !cd.lifestyle_breakdown) return;
    const lb = cd.lifestyle_breakdown;
    el.innerHTML = `<div class="detail-grid">
      ${row('Stress',         lb.stress.toFixed(0)        + ' / 100')}
      ${row('Smoking',        lb.smoking.toFixed(0)       + ' / 100')}
      ${row('Sleep quality',  lb.sleep.toFixed(0)         + ' / 100')}
      ${row('Diet & exercise',lb.diet_exercise.toFixed(0) + ' / 100')}
      ${row('Comorbidities',  lb.comorbidities.toFixed(0) + ' / 100')}
    </div>`;
  }

  function renderGeneticDetail(gd) {
    const el = document.getElementById('detailGenetic');
    if (!el) return;
    el.innerHTML = `
      <div class="detail-grid">
        ${row('CAG repeats', `${gd.cag_repeats} (${gd.cag_risk_label || gd.cag_risk_level})`)}
        ${row('GGN repeats', `${gd.ggn_repeats} (${gd.ggn_risk_level})`)}
        ${row('Sequence length', gd.sequence_length + ' bp')}
        ${row('SNPs analyzed', `${(gd.snp_results || []).length} / 9`)}
      </div>
      <p style="margin-top:var(--s-3);font-size:0.9rem;color:var(--ink-600);line-height:1.55;">${gd.cag_interpretation || ''}</p>`;
  }

  // ── localStorage form persistence ─────────────────────────────────────

  function saveProgress() {
    try { localStorage.setItem('baldguard_form_v2', JSON.stringify(collectFormData())); } catch (_) {}
  }

  function loadProgress() {
    try {
      const raw = localStorage.getItem('baldguard_form_v2');
      if (!raw) return;
      const data = JSON.parse(raw);
      const s1 = data.section1; if (!s1) return;

      if (s1.age) { const el = document.getElementById('age'); if (el) el.value = s1.age; }
      if (s1.gender) {
        const gv = (s1.gender === 'pria') ? 'male' : (s1.gender === 'wanita') ? 'female' : s1.gender;
        const radio = document.querySelector(`input[name="gender"][value="${gv}"]`);
        if (radio) { radio.checked = true; radio.dispatchEvent(new Event('change')); }
      }
      if (s1.ethnicity) { const el = document.getElementById('ethnicity'); if (el) el.value = s1.ethnicity; }
    } catch (_) { /* ignore stale data */ }
  }

  // ── Plain-text report download (English) ──────────────────────────────

  function downloadReport() {
    const r = window._baldguardResult;
    if (!r) { alert('Run an analysis first.'); return; }

    const cmp = r.ncbi_comparison || {};
    const conf = r.confidence || {};
    const lines = [
      'BALDGUARD — EARLY-WARNING HAIR-LOSS RISK ASSESSMENT',
      '====================================================',
      `Date              : ${new Date().toLocaleDateString('en-US', { dateStyle: 'full' })}`,
      `Analysis type     : ${r.analysis_type}`,
      `Confidence level  : ${conf.label || '—'} (${conf.percent || 0}%)`,
      '',
      `OVERALL RISK SCORE: ${r.scores.hybrid_score.toFixed(1)} / 100`,
      `RISK CATEGORY     : ${r.risk_category_label || r.risk_category}`,
      `DESCRIPTION       : ${r.risk_description}`,
      '',
      'COMPONENT SCORES:',
      `  • Clinical         : ${r.scores.clinical_score.toFixed(1)} / 100`,
      `  • Family history   : ${r.scores.family_score.toFixed(1)} / 100`,
      `  • Lifestyle        : ${r.scores.lifestyle_score.toFixed(1)} / 100`,
    ];
    if (r.scores.genetic_score > 0) {
      lines.push(`  • Genetic          : ${r.scores.genetic_score.toFixed(1)} / 100`);
    }
    lines.push('',
      'NCBI REFERENCE COMPARISON:',
      `  • NCBI reference (${cmp.ncbi_accession || 'NM_000044.6'}): ${cmp.ncbi_reference_cag || 22} CAG repeats`,
      `  • Your AR profile        : ${cmp.user_cag_midpoint || '—'} CAG (` +
        (cmp.user_value_type === 'measured' ? 'measured' : `estimated, range ${cmp.user_cag_min}–${cmp.user_cag_max}`) + `)`,
      `  • Interpretation         : ${cmp.interpretation || ''}`,
    );
    if (r.genetic_details) {
      const gd = r.genetic_details;
      lines.push('', 'GENETIC DATA:',
        `  • CAG repeats: ${gd.cag_repeats} (${gd.cag_risk_label || gd.cag_risk_level})`,
        `  • GGN repeats: ${gd.ggn_repeats} (${gd.ggn_risk_level})`);
    }
    lines.push('', 'RECOMMENDATIONS:');
    (r.recommendations || []).forEach((rec, i) => lines.push(`  ${i + 1}. ${rec}`));
    lines.push('', '---',
      `DISCLAIMER: ${r.disclaimer}`,
      '',
      'BaldGuard — Educational computational-biology project');

    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `baldguard_report_${Date.now()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
  }

  window.downloadPDF = downloadReport;

  // ── Main entry point ───────────────────────────────────────────────────

  async function processResults(withGenetic) {
    const spinner   = document.getElementById('loadingSpinner');
    const container = document.getElementById('resultsContainer');

    try {
      const requestData = collectFormData();
      const geneticData = withGenetic ? collectGeneticData() : null;
      if (geneticData) requestData.genetic_data = geneticData;

      const result = await analyzeRisk(requestData);
      window._baldguardResult = result;

      applyResults(result);
      saveProgress();

      if (spinner)   spinner.style.display   = 'none';
      if (container) container.style.display = 'block';

      if (typeof window.BaldGuardCharts !== 'undefined') {
        window.BaldGuardCharts.init(result.analysis_type !== 'clinical_only');
      }
    } catch (err) {
      console.warn('BaldGuard API error:', err.message);
      if (spinner)   spinner.style.display   = 'none';
      if (container) container.style.display = 'block';
      if (typeof window.showMockResults === 'function') {
        window.showMockResults(withGenetic);
      }
    }
  }

  document.addEventListener('DOMContentLoaded', loadProgress);
  window.BaldGuardMain = { processResults, collectFormData, downloadReport };
})();
