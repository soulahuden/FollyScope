// main.js — Integrasi API BaldGuard dengan analyze.html
// Mengintegrasikan form data dengan backend FastAPI.
// Exposed via window.BaldGuardMain.processResults(withGenetic)

(function () {
  'use strict';

  // ── Form data collection ────────────────────────────────────────────────

  function getVal(id) {
    const el = document.getElementById(id);
    return el ? el.value : null;
  }
  function getNum(id) {
    const v = parseInt(getVal(id), 10);
    return isNaN(v) ? null : v;
  }
  function getFloat(id) {
    const v = parseFloat(getVal(id));
    return isNaN(v) ? null : v;
  }
  function getChecked(id) {
    const el = document.getElementById(id);
    return el ? el.checked : false;
  }
  function getRadio(name) {
    const el = document.querySelector(`input[name="${name}"]:checked`);
    return el ? el.value : null;
  }
  function getCheckboxList(name) {
    return Array.from(document.querySelectorAll(`input[name="${name}"]:checked`))
      .map(e => e.value)
      .filter(v => v && v !== 'none');
  }

  function collectFormData() {
    const gender = getRadio('gender') || 'male';

    const section1 = {
      age:          getNum('age') || 30,
      gender:       gender === 'male' ? 'pria' : 'wanita',
      ethnicity:    getVal('ethnicity') || 'Asia',
      puberty_age:  getNum('puberty_age'),
    };

    // Norwood (male) or Ludwig (female)
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

    const section3 = {
      hair_pull_count: getNum('pull_test'),
    };

    const fatherBald            = getRadio('father_bald') === 'yes';
    const maternalGfBald        = getRadio('maternal_gf_bald') === 'yes';
    const paternalGfBald        = getRadio('paternal_gf_bald') === 'yes';
    const brothersBald          = getRadio('brothers_bald') === 'yes';
    const motherThinning        = getRadio('mother_thinning') === 'yes';
    const sistersThinningRaw    = getRadio('sisters_thinning');

    const section4 = {
      father_bald:                    fatherBald,
      father_bald_age:                fatherBald ? getNum('father_bald_age') : null,
      maternal_grandfather_bald:      maternalGfBald,
      maternal_grandfather_bald_age:  maternalGfBald ? getNum('maternal_gf_bald_age') : null,
      paternal_grandfather_bald:      paternalGfBald,
      brothers_bald:                  brothersBald,
      mother_thinning:                motherThinning,
      generations_bald:               getNum('generations') || 0,
      sisters_thinning:               sistersThinningRaw === 'yes' ? true
                                    : sistersThinningRaw === 'no'  ? false
                                    : null,
    };

    const section5 = {
      stress_level:          getNum('stress') || 5,
      sleep_hours:           getFloat('sleep') || 7.0,
      smoking:               getChecked('smoking'),
      cigarettes_per_day:    getChecked('smoking') ? (getNum('cigarettes_per_day') || 0) : 0,
      alcohol_frequency:     getVal('alcohol') || 'tidak_pernah',
      diet_quality:          getRadio('diet_quality') || 'seimbang',
      exercise_frequency:    getRadio('exercise_frequency') || 'sedang',
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

    // Jika ada hasil dari 23andMe upload, gunakan itu
    if (window._23andmeGenotypes && Object.keys(window._23andmeGenotypes).length > 0) {
      Object.assign(snpGenotypes, window._23andmeGenotypes);
    }

    // Tambah/override dengan input manual dari tabel (manual input lebih prioritas)
    document.querySelectorAll('#snpTableBody select').forEach(sel => {
      const rsid = sel.name?.replace('snp_', '');
      if (rsid && sel.value && sel.value !== 'unknown') {
        snpGenotypes[rsid] = sel.value;
      }
    });

    const hasFasta = fastaText.length > 0;
    const hasSnp   = Object.keys(snpGenotypes).length > 0;

    if (!hasFasta && !hasSnp) return null;

    return {
      fasta_sequence: hasFasta ? fastaText : undefined,
      snp_genotypes:  hasSnp   ? snpGenotypes : undefined,
    };
  }

  // ── Result display ─────────────────────────────────────────────────────

  function categoryLabel(cat) {
    const map = {
      MINIMAL: 'MINIMAL', RENDAH: 'RENDAH', SEDANG: 'SEDANG',
      TINGGI: 'TINGGI', SANGAT_TINGGI: 'SANGAT TINGGI',
    };
    return map[cat] || cat;
  }

  function applyResults(result) {
    const scores = result.scores;
    const color  = result.risk_color || '#e74c3c';

    // Gauge & score
    const gaugeMarker = document.getElementById('gaugeMarker');
    if (gaugeMarker) gaugeMarker.style.left = Math.min(scores.hybrid_score, 100) + '%';

    const scoreEl = document.getElementById('riskScore');
    if (scoreEl) { scoreEl.textContent = scores.hybrid_score.toFixed(1); scoreEl.style.color = color; }

    const catEl = document.getElementById('riskCategory');
    if (catEl) {
      catEl.textContent = categoryLabel(result.risk_category);
      catEl.style.background = color + '22';
      catEl.style.color = color;
    }

    const badgeEl = document.getElementById('analysisTypeBadge');
    if (badgeEl) {
      const typeMap = {
        hybrid:       '<i class="fa-solid fa-dna"></i> Analisis Hybrid (Genetik + Klinis)',
        clinical_only:'<i class="fa-solid fa-clipboard-list"></i> Analisis Klinis Saja',
        genetic_only: '<i class="fa-solid fa-dna"></i> Analisis Genetik Saja',
      };
      badgeEl.innerHTML = typeMap[result.analysis_type] || result.analysis_type;
    }

    // Score cards
    function setCard(valId, barId, score, notApplicable) {
      const val = document.getElementById(valId);
      const bar = document.getElementById(barId);
      if (val) val.textContent = notApplicable ? 'N/A' : score.toFixed(1);
      if (bar) bar.style.width  = notApplicable ? '0%'  : score + '%';
    }

    const noGenetic = result.analysis_type !== 'hybrid';
    setCard('geneticScoreVal',   'geneticScoreBar',   scores.genetic_score,   noGenetic);
    setCard('clinicalScoreVal',  'clinicalScoreBar',  scores.clinical_score,  false);
    setCard('familyScoreVal',    'familyScoreBar',    scores.family_score,    false);
    setCard('lifestyleScoreVal', 'lifestyleScoreBar', scores.lifestyle_score, false);

    // SNP card visibility
    const snpCard = document.getElementById('snpHeatmapCard');
    const genCard = document.getElementById('geneticDetailCard');
    const hasGeneticData = result.analysis_type === 'hybrid' || result.analysis_type === 'genetic_only';
    if (snpCard) snpCard.style.display = hasGeneticData ? 'block' : 'none';
    if (genCard) genCard.style.display = hasGeneticData ? 'block' : 'none';

    // Recommendations
    const recList = document.getElementById('recommendationsList');
    if (recList && result.recommendations) {
      const icons = ['fa-user-doctor','fa-moon','fa-apple-whole','fa-spa','fa-scissors','fa-vial','fa-pills','fa-heart-pulse'];
      const iconColors = ['#27ae60','#3498db','#f39c12','#9b59b6','#e67e22','#1abc9c','#e74c3c','#34495e'];
      recList.innerHTML = result.recommendations.map((rec, i) => {
        const ic = icons[i % icons.length];
        const cl = iconColors[i % iconColors.length];
        return `<li class="rec-item"><span class="rec-icon"><i class="fa-solid ${ic}" style="color:${cl};"></i></span><span>${rec}</span></li>`;
      }).join('');
    }

    // Collapsible detail bodies
    const cd = result.clinical_details;
    const detailClinical = document.getElementById('detailClinical');
    if (detailClinical && cd) {
      detailClinical.innerHTML = `
        <div class="detail-grid">
          <div class="detail-item"><span>Skala Norwood/Ludwig:</span><strong>${cd.norwood_ludwig_score.toFixed(0)}/100</strong></div>
          <div class="detail-item"><span>Pola & Area:</span><strong>${cd.pattern_area_score.toFixed(0)}/100</strong></div>
          <div class="detail-item"><span>Hair Pull Test:</span><strong>${cd.hair_pull_score.toFixed(0)}/100</strong></div>
          <div class="detail-item"><span>Volume Rontok:</span><strong>${cd.loss_volume_score.toFixed(0)}/100</strong></div>
          <div class="detail-item"><span>Miniaturisasi:</span><strong>${cd.miniaturization_score.toFixed(0)}/100</strong></div>
          <div class="detail-item"><span>Durasi Gejala:</span><strong>${cd.duration_score.toFixed(0)}/100</strong></div>
        </div>`;
    }

    const detailFamily = document.getElementById('detailFamily');
    if (detailFamily && cd && cd.family_breakdown) {
      const fb = cd.family_breakdown;
      detailFamily.innerHTML = `
        <div class="detail-grid">
          <div class="detail-item"><span>⚠ Kakek dari Ibu (X-linked):</span><strong>${fb.maternal_grandfather.toFixed(0)}/100</strong></div>
          <div class="detail-item"><span>Ayah:</span><strong>${fb.father.toFixed(0)}/100</strong></div>
          <div class="detail-item"><span>Kakek dari Ayah:</span><strong>${fb.paternal_grandfather.toFixed(0)}/100</strong></div>
          <div class="detail-item"><span>Saudara Laki-laki:</span><strong>${fb.brothers.toFixed(0)}/100</strong></div>
          <div class="detail-item"><span>Ibu:</span><strong>${fb.mother.toFixed(0)}/100</strong></div>
        </div>`;
    }

    const detailLifestyle = document.getElementById('detailLifestyle');
    if (detailLifestyle && cd && cd.lifestyle_breakdown) {
      const lb = cd.lifestyle_breakdown;
      detailLifestyle.innerHTML = `
        <div class="detail-grid">
          <div class="detail-item"><span>Stres:</span><strong>${lb.stress.toFixed(0)}/100</strong></div>
          <div class="detail-item"><span>Merokok:</span><strong>${lb.smoking.toFixed(0)}/100</strong></div>
          <div class="detail-item"><span>Kualitas Tidur:</span><strong>${lb.sleep.toFixed(0)}/100</strong></div>
          <div class="detail-item"><span>Diet & Olahraga:</span><strong>${lb.diet_exercise.toFixed(0)}/100</strong></div>
          <div class="detail-item"><span>Komorbiditas:</span><strong>${lb.comorbidities.toFixed(0)}/100</strong></div>
        </div>`;
    }

    if (hasGeneticData && result.genetic_details) {
      const gd = result.genetic_details;
      const detailGenetic = document.getElementById('detailGenetic');
      if (detailGenetic) {
        detailGenetic.innerHTML = `
          <div class="detail-grid">
            <div class="detail-item"><span>CAG Repeats:</span><strong>${gd.cag_repeats} (${gd.cag_risk_level})</strong></div>
            <div class="detail-item"><span>GGN Repeats:</span><strong>${gd.ggn_repeats} (${gd.ggn_risk_level})</strong></div>
            <div class="detail-item"><span>Panjang Sekuens:</span><strong>${gd.sequence_length} bp</strong></div>
            <div class="detail-item"><span>SNP Teranalisis:</span><strong>${(gd.snp_results||[]).length}/9</strong></div>
          </div>
          <p style="margin-top:.6rem;font-style:italic;color:#666;font-size:.88rem;">${gd.cag_interpretation}</p>`;
      }
    }
  }

  // ── Save / Restore localStorage ────────────────────────────────────────

  function saveProgress() {
    try {
      const data = collectFormData();
      localStorage.setItem('baldguard_form_v1', JSON.stringify(data));
    } catch (e) { /* ignore */ }
  }

  function loadProgress() {
    try {
      const raw = localStorage.getItem('baldguard_form_v1');
      if (!raw) return;
      const data = JSON.parse(raw);
      const s1 = data.section1;
      if (!s1) return;

      if (s1.age) {
        const el = document.getElementById('age');
        if (el) el.value = s1.age;
      }
      if (s1.gender) {
        const genderVal = s1.gender === 'pria' ? 'male' : 'female';
        const radio = document.querySelector(`input[name="gender"][value="${genderVal}"]`);
        if (radio) {
          radio.checked = true;
          radio.dispatchEvent(new Event('change'));
        }
      }
      if (s1.ethnicity) {
        const el = document.getElementById('ethnicity');
        if (el) el.value = s1.ethnicity;
      }
    } catch (e) { /* ignore stale data */ }
  }

  // ── Download report ────────────────────────────────────────────────────

  function downloadReport() {
    const result = window._baldguardResult;
    if (!result) {
      alert('Belum ada hasil analisis. Silakan jalankan analisis terlebih dahulu.');
      return;
    }
    const r = result;
    const lines = [
      'LAPORAN ANALISIS RISIKO KEBOTAKAN DINI — BALDGUARD',
      '====================================================',
      `Tanggal          : ${new Date().toLocaleDateString('id-ID', { dateStyle: 'full' })}`,
      `Jenis Analisis   : ${r.analysis_type}`,
      '',
      `SKOR RISIKO      : ${r.scores.hybrid_score.toFixed(1)} / 100`,
      `KATEGORI RISIKO  : ${r.risk_category}`,
      `DESKRIPSI        : ${r.risk_description}`,
      '',
      'KOMPONEN SKOR:',
      `  • Klinis         : ${r.scores.clinical_score.toFixed(1)} / 100`,
      `  • Riwayat Keluarga: ${r.scores.family_score.toFixed(1)} / 100`,
      `  • Gaya Hidup     : ${r.scores.lifestyle_score.toFixed(1)} / 100`,
    ];
    if (r.scores.genetic_score > 0) {
      lines.push(`  • Genetik        : ${r.scores.genetic_score.toFixed(1)} / 100`);
    }
    if (r.genetic_details) {
      const gd = r.genetic_details;
      lines.push('', 'DATA GENETIK:', `  • CAG Repeats    : ${gd.cag_repeats} (${gd.cag_risk_level})`, `  • GGN Repeats    : ${gd.ggn_repeats} (${gd.ggn_risk_level})`);
    }
    lines.push('', 'REKOMENDASI:');
    (r.recommendations || []).forEach((rec, i) => lines.push(`  ${i + 1}. ${rec}`));
    lines.push('', '---', `DISCLAIMER: ${r.disclaimer}`, '', 'BaldGuard — Project UAS Computational Biology');

    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `baldguard_laporan_${Date.now()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
  }

  // Override analyze.html's downloadPDF to use our real report
  window.downloadPDF = downloadReport;

  // ── Main entry point called by analyze.html ────────────────────────────

  async function processResults(withGenetic) {
    const spinner   = document.getElementById('loadingSpinner');
    const container = document.getElementById('resultsContainer');

    try {
      const formData     = collectFormData();
      const geneticData  = withGenetic ? collectGeneticData() : null;
      const requestData  = { ...formData };
      if (geneticData) requestData.genetic_data = geneticData;

      // Call real backend
      const result = await analyzeRisk(requestData);
      window._baldguardResult = result;

      // Update DOM
      applyResults(result);
      saveProgress();

      if (spinner)   spinner.style.display   = 'none';
      if (container) container.style.display = 'block';

      // Render charts
      if (typeof window.BaldGuardCharts !== 'undefined') {
        window.BaldGuardCharts.init(withGenetic);
      }

    } catch (err) {
      // Backend unreachable or validation error — fall back to mock results
      console.warn('BaldGuard API error, showing mock results:', err.message);
      if (spinner)   spinner.style.display   = 'none';
      if (container) container.style.display = 'block';
      if (typeof window.showMockResults === 'function') {
        window.showMockResults(withGenetic);
      }
    }
  }

  // Auto-restore form on page load
  document.addEventListener('DOMContentLoaded', () => {
    loadProgress();
  });

  // Expose public API
  window.BaldGuardMain = { processResults, collectFormData, downloadReport };
})();
