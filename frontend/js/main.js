// main.js — Folliscope front-end integration
// Collects questionnaire data, calls /api/analyze, and renders the
// risk profile, NCBI comparison, confidence indicator, and phenotype
// inference returned by the backend.
// Exposed via window.FolliscopeMain.processResults(withGenetic).

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
    try { localStorage.setItem('folliscope_form_v2', JSON.stringify(collectFormData())); } catch (_) {}
  }

  function loadProgress() {
    try {
      const raw = localStorage.getItem('folliscope_form_v2');
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

  // ── Structured PDF report (jsPDF, client-side) ───────────────────────

  function downloadReport() {
    const r = window._folliscopeResult;
    if (!r) { alert('Run an analysis first.'); return; }

    if (!window.jspdf || !window.jspdf.jsPDF) {
      console.warn('jsPDF not loaded; falling back to plain text.');
      return downloadReportText(r);
    }
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ unit: 'pt', format: 'a4' });

    const PAGE_W = doc.internal.pageSize.getWidth();
    const PAGE_H = doc.internal.pageSize.getHeight();
    const M = 48;                                // margin
    let y = M;

    const INK_900 = [15, 23, 42];
    const INK_600 = [71, 85, 105];
    const INK_400 = [148, 163, 184];
    const BRAND   = [5, 150, 105];
    const cmp     = r.ncbi_comparison || {};
    const conf    = r.confidence || {};

    // ─── Risk color matching the UI palette ───────────────────────────
    const RISK_COLOR = {
      MINIMAL:       [16, 185, 129],
      RENDAH:        [34, 197, 94],
      SEDANG:        [245, 158, 11],
      TINGGI:        [249, 115, 22],
      SANGAT_TINGGI: [220, 38, 38],
    };
    const riskRGB = RISK_COLOR[r.risk_category] || [148, 163, 184];

    // ─── Header band ──────────────────────────────────────────────────
    doc.setFillColor(...INK_900);
    doc.rect(0, 0, PAGE_W, 96, 'F');
    doc.setFillColor(...BRAND);
    doc.rect(M, 30, 36, 36, 'F');
    doc.setTextColor(255, 255, 255);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(11);
    doc.text('Fs', M + 10, 53);

    doc.setFontSize(20);
    doc.text('Folliscope', M + 52, 50);
    doc.setFontSize(9);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(167, 243, 208);
    doc.text('Early-warning hair-loss risk assessment', M + 52, 66);

    doc.setTextColor(148, 163, 184);
    doc.setFontSize(8);
    const dateStr = new Date().toLocaleDateString('en-US',
      { year: 'numeric', month: 'long', day: 'numeric' });
    doc.text(dateStr, PAGE_W - M, 50, { align: 'right' });
    doc.text(r.analysis_type.replace(/_/g, ' '), PAGE_W - M, 64, { align: 'right' });

    y = 130;

    // ─── Headline score + risk category ───────────────────────────────
    doc.setTextColor(...INK_400);
    doc.setFontSize(9);
    doc.text('OVERALL RISK SCORE', M, y);
    y += 6;

    doc.setTextColor(...riskRGB);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(48);
    doc.text(r.scores.hybrid_score.toFixed(1), M, y + 36);

    doc.setFontSize(11);
    doc.setTextColor(...INK_600);
    doc.text(' / 100', M + doc.getTextWidth(r.scores.hybrid_score.toFixed(1)) + 4, y + 36);

    // Risk pill
    const pillX = M + 200;
    const pillY = y + 12;
    doc.setFillColor(riskRGB[0], riskRGB[1], riskRGB[2]);
    doc.roundedRect(pillX, pillY, 120, 28, 14, 14, 'F');
    doc.setTextColor(255, 255, 255);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(11);
    doc.text((r.risk_category_label || r.risk_category) + ' RISK',
             pillX + 60, pillY + 18, { align: 'center' });

    // Gauge bar
    y += 60;
    const gaugeX = M;
    const gaugeW = PAGE_W - 2 * M;
    const gaugeY = y;
    // gradient simulated with 5 segments
    const segments = [
      [16, 185, 129], [34, 197, 94], [245, 158, 11], [249, 115, 22], [220, 38, 38]
    ];
    segments.forEach((rgb, i) => {
      doc.setFillColor(...rgb);
      doc.rect(gaugeX + (gaugeW / 5) * i, gaugeY, gaugeW / 5, 10, 'F');
    });
    // marker
    const markX = gaugeX + (gaugeW * Math.min(r.scores.hybrid_score, 100) / 100);
    doc.setFillColor(...INK_900);
    doc.rect(markX - 1.5, gaugeY - 4, 3, 18, 'F');

    doc.setTextColor(...INK_400);
    doc.setFontSize(7);
    doc.text('0 · Minimal', gaugeX, gaugeY + 22);
    doc.text('50', gaugeX + gaugeW/2, gaugeY + 22, { align: 'center' });
    doc.text('100 · Very high', gaugeX + gaugeW, gaugeY + 22, { align: 'right' });

    y += 40;

    // Description
    doc.setTextColor(...INK_600);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(10);
    const descLines = doc.splitTextToSize(r.risk_description || '', gaugeW);
    doc.text(descLines, M, y);
    y += descLines.length * 13 + 16;

    // ─── Confidence ───────────────────────────────────────────────────
    doc.setDrawColor(...INK_400);
    doc.setLineWidth(0.5);
    doc.line(M, y, PAGE_W - M, y);
    y += 14;

    doc.setFontSize(9);
    doc.setTextColor(...INK_400);
    doc.text('CONFIDENCE IN THIS RESULT', M, y);
    doc.setTextColor(...INK_900);
    doc.setFont('helvetica', 'bold');
    doc.text(`${conf.percent || 0}%`, PAGE_W - M, y, { align: 'right' });
    y += 8;

    doc.setDrawColor(...INK_400);
    doc.setFillColor(226, 232, 240);
    doc.rect(M, y, gaugeW, 4, 'F');
    doc.setFillColor(...BRAND);
    doc.rect(M, y, gaugeW * (conf.percent || 0) / 100, 4, 'F');
    y += 14;

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9);
    doc.setTextColor(...INK_600);
    const confLines = doc.splitTextToSize(conf.description || '', gaugeW);
    doc.text(confLines, M, y);
    y += confLines.length * 12 + 14;

    // ─── NCBI Comparison ──────────────────────────────────────────────
    doc.setDrawColor(...INK_400);
    doc.line(M, y, PAGE_W - M, y);
    y += 14;

    doc.setFontSize(11);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...INK_900);
    doc.text('NCBI reference vs. your profile', M, y);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8);
    doc.setTextColor(...INK_400);
    doc.text(cmp.ncbi_accession || 'NM_000044.6', PAGE_W - M, y, { align: 'right' });
    y += 18;

    // Comparison table
    const ncbiCag = cmp.ncbi_reference_cag || 22;
    const userCagText = cmp.user_value_type === 'measured'
      ? `${cmp.user_cag_midpoint} CAG (measured)`
      : `${cmp.user_cag_midpoint} CAG (estimated · range ${cmp.user_cag_min}–${cmp.user_cag_max})`;

    doc.setFontSize(9);
    doc.setTextColor(...INK_600);
    doc.text('NCBI reference', M, y);
    doc.setTextColor(...INK_900);
    doc.setFont('helvetica', 'bold');
    doc.text(`${ncbiCag} CAG repeats`, M + 200, y);
    y += 14;
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(...INK_600);
    doc.text('Your AR profile', M, y);
    doc.setTextColor(...INK_900);
    doc.setFont('helvetica', 'bold');
    doc.text(userCagText, M + 200, y);
    y += 18;

    // Interpretation paragraph
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(...INK_600);
    doc.setFontSize(9);
    const interpLines = doc.splitTextToSize(cmp.interpretation || '', gaugeW);
    doc.text(interpLines, M, y);
    y += interpLines.length * 12 + 8;

    // Reasoning
    if (cmp.inference_reasoning && cmp.inference_reasoning.length) {
      doc.setFontSize(8);
      doc.setTextColor(...INK_400);
      doc.text('WHY THIS ESTIMATE', M, y);
      y += 10;
      doc.setFontSize(9);
      doc.setTextColor(...INK_600);
      cmp.inference_reasoning.forEach(reason => {
        const lines = doc.splitTextToSize('• ' + reason, gaugeW - 12);
        doc.text(lines, M + 6, y);
        y += lines.length * 12 + 2;
      });
      y += 6;
    }

    // ─── Component scores ─────────────────────────────────────────────
    if (y > PAGE_H - 220) { doc.addPage(); y = M; }

    doc.setDrawColor(...INK_400);
    doc.line(M, y, PAGE_W - M, y);
    y += 14;
    doc.setFontSize(11);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...INK_900);
    doc.text('Component scores', M, y);
    y += 16;

    const components = [
      ['Clinical',       r.scores.clinical_score],
      ['Family history', r.scores.family_score],
      ['Lifestyle',      r.scores.lifestyle_score],
    ];
    if (r.scores.genetic_score > 0) components.unshift(['Genetic', r.scores.genetic_score]);

    components.forEach(([label, score]) => {
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(9);
      doc.setTextColor(...INK_600);
      doc.text(label, M, y);
      doc.setTextColor(...INK_900);
      doc.setFont('helvetica', 'bold');
      doc.text(score.toFixed(1) + ' / 100', M + 200, y);
      // bar
      doc.setFillColor(226, 232, 240);
      doc.rect(M + 280, y - 6, gaugeW - 280, 4, 'F');
      doc.setFillColor(...BRAND);
      doc.rect(M + 280, y - 6, (gaugeW - 280) * Math.min(score, 100) / 100, 4, 'F');
      y += 16;
    });

    // ─── Recommendations ──────────────────────────────────────────────
    if (y > PAGE_H - 180) { doc.addPage(); y = M; }
    y += 8;
    doc.setDrawColor(...INK_400);
    doc.line(M, y, PAGE_W - M, y);
    y += 14;
    doc.setFontSize(11);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(...INK_900);
    doc.text('Recommendations', M, y);
    y += 16;
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9);
    doc.setTextColor(...INK_600);
    (r.recommendations || []).forEach((rec, i) => {
      if (y > PAGE_H - 80) { doc.addPage(); y = M; }
      const lines = doc.splitTextToSize(`${i + 1}.  ${rec}`, gaugeW - 4);
      doc.text(lines, M, y);
      y += lines.length * 12 + 4;
    });

    // ─── Footer disclaimer (every page) ───────────────────────────────
    const pageCount = doc.getNumberOfPages();
    for (let p = 1; p <= pageCount; p++) {
      doc.setPage(p);
      doc.setDrawColor(...INK_400);
      doc.setLineWidth(0.3);
      doc.line(M, PAGE_H - 50, PAGE_W - M, PAGE_H - 50);
      doc.setFontSize(7);
      doc.setTextColor(...INK_400);
      const disclaimer = r.disclaimer || 'Educational risk assessment only — not a medical diagnosis.';
      const dLines = doc.splitTextToSize(disclaimer, PAGE_W - 2 * M);
      doc.text(dLines, M, PAGE_H - 38);
      doc.text(`Folliscope · page ${p} / ${pageCount}`, PAGE_W - M, PAGE_H - 20, { align: 'right' });
    }

    doc.save(`folliscope_report_${Date.now()}.pdf`);
  }

  // Fallback plain-text writer (if jsPDF fails to load)
  function downloadReportText(r) {
    const lines = [
      'FOLLISCOPE — EARLY-WARNING HAIR-LOSS RISK ASSESSMENT',
      `Score: ${r.scores.hybrid_score.toFixed(1)} / 100`,
      `Category: ${r.risk_category_label || r.risk_category}`,
      `Confidence: ${r.confidence?.percent || 0}%`,
      '',
      r.risk_description || '',
      '',
      'Recommendations:',
      ...(r.recommendations || []).map((rec, i) => `  ${i + 1}. ${rec}`),
      '',
      r.disclaimer || '',
    ];
    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `folliscope_report_${Date.now()}.txt`;
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
      window._folliscopeResult = result;
      window._folliscopeOriginalGenetic = geneticData || null;

      applyResults(result);
      saveProgress();

      // Prefill the treatment simulator with the user's actual lifestyle values
      if (typeof window.prefillSimulator === 'function') {
        window.prefillSimulator(requestData);
      }

      if (spinner)   spinner.style.display   = 'none';
      if (container) container.style.display = 'block';

      if (typeof window.FolliscopeCharts !== 'undefined') {
        window.FolliscopeCharts.init(result.analysis_type !== 'clinical_only');
      }
    } catch (err) {
      console.warn('Folliscope API error:', err.message);
      if (spinner)   spinner.style.display   = 'none';
      if (container) container.style.display = 'block';
      if (typeof window.showMockResults === 'function') {
        window.showMockResults(withGenetic);
      }
    }
  }

  document.addEventListener('DOMContentLoaded', loadProgress);
  window.FolliscopeMain = { processResults, collectFormData, downloadReport };
})();
