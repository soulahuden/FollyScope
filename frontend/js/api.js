// api.js — Backend communication layer for BaldGuard
// Handles all HTTP requests to the FastAPI backend at /api/

const API_BASE = '/api';

/**
 * Generic JSON fetch wrapper.
 * Throws a descriptive Error on non-2xx responses.
 *
 * @param {string} url
 * @param {RequestInit} options
 * @returns {Promise<any>}
 */
async function fetchJSON(url, options = {}) {
    const response = await fetch(url, {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        ...options,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
}

// ── Health & Info endpoints ───────────────────────────────────

/**
 * Ping the backend health endpoint.
 * @returns {Promise<{status: string, version: string}>}
 */
async function checkHealth() {
    return fetchJSON(`${API_BASE}/health`);
}

/**
 * Fetch full SNP database with metadata.
 * @returns {Promise<{snps: Array, total: number}>}
 */
async function getSNPDatabase() {
    return fetchJSON(`${API_BASE}/snp-database`);
}

/**
 * Fetch available analysis information / model metadata.
 * @returns {Promise<any>}
 */
async function getAnalysisInfo() {
    return fetchJSON(`${API_BASE}/info`);
}

// ── Main analysis endpoint ────────────────────────────────────

/**
 * Run the full risk analysis against the backend.
 *
 * @param {Object} requestData - Structured form payload:
 *   {
 *     section1: { age, gender, ethnicity, puberty_age },
 *     section2: { hair_loss_per_day, loss_duration_months, ... },
 *     section3: { hair_pull_count },
 *     section4: { father_bald, maternal_grandfather_bald, ... },
 *     section5: { stress_level, sleep_hours, smoking, ... },
 *     genetic_data?: { fasta_sequence?, snp_genotypes? }
 *   }
 * @returns {Promise<AnalysisResult>}
 */
async function analyzeRisk(requestData) {
    return fetchJSON(`${API_BASE}/analyze`, {
        method: 'POST',
        body: JSON.stringify(requestData),
    });
}

// ── Genetic data endpoints ─────────────────────────────────────

/**
 * Upload a FASTA file to the backend for parsing.
 * Returns parsed CAG/GGN repeat counts and sequence stats.
 *
 * @param {File} file
 * @returns {Promise<{cag_repeats: number, ggn_repeats: number, sequence_length: number}>}
 */
async function uploadFasta(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/analyze/fasta-upload`, {
        method: 'POST',
        body: formData,
        // Note: do NOT set Content-Type here; browser sets multipart boundary
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'FASTA upload failed');
    }

    return response.json();
}

/**
 * Parse FASTA text directly (alternative to file upload).
 *
 * @param {string} fastaText
 * @returns {Promise<{cag_repeats: number, ggn_repeats: number, sequence_length: number}>}
 */
async function parseFastaText(fastaText) {
    return fetchJSON(`${API_BASE}/analyze/parse-fasta`, {
        method: 'POST',
        body: JSON.stringify({ fasta_sequence: fastaText }),
    });
}

// ── Sample data loaders ────────────────────────────────────────

/**
 * Load a pre-built sample FASTA file served from the /sample_data/ static route.
 *
 * @param {'high_risk'|'medium_risk'|'low_risk'|'protective'} profile
 * @returns {Promise<string>} Raw FASTA text
 */
async function loadSampleFasta(profile) {
    const response = await fetch(`/sample_data/${profile}_sample.fasta`);
    if (!response.ok) {
        throw new Error(`Could not load sample FASTA for profile "${profile}"`);
    }
    return response.text();
}

/**
 * Load a pre-built sample genotype TSV file.
 *
 * @param {'high_risk'|'medium_risk'|'low_risk'} profile
 * @returns {Promise<string>} Raw TSV text
 */
async function loadSampleGenotype(profile) {
    const response = await fetch(`/sample_data/${profile}_genotype.tsv`);
    if (!response.ok) {
        throw new Error(`Could not load sample genotype for profile "${profile}"`);
    }
    return response.text();
}

// ── Utility: request with retry ───────────────────────────────

/**
 * Wrapper that retries a fetch up to `maxRetries` times on network error.
 *
 * @param {Function} fn  - async function returning a promise
 * @param {number}   maxRetries
 * @param {number}   delayMs
 * @returns {Promise<any>}
 */
async function withRetry(fn, maxRetries = 2, delayMs = 800) {
    let lastError;
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
            return await fn();
        } catch (err) {
            lastError = err;
            if (attempt < maxRetries) {
                await new Promise(resolve => setTimeout(resolve, delayMs * (attempt + 1)));
            }
        }
    }
    throw lastError;
}

/**
 * Check backend availability with a timeout.
 * Resolves true/false — does not throw.
 *
 * @param {number} timeoutMs
 * @returns {Promise<boolean>}
 */
async function isBackendAvailable(timeoutMs = 3000) {
    try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), timeoutMs);
        await fetch(`${API_BASE}/health`, { signal: controller.signal });
        clearTimeout(timer);
        return true;
    } catch {
        return false;
    }
}

// ── NCBI & 23andMe endpoints ──────────────────────────────────────────────────

/**
 * Fetch the NCBI RefSeq AR reference sequence (NM_000044.6).
 * @returns {Promise<NCBIReferenceResult>}
 */
async function fetchARReference() {
    return fetchJSON(`${API_BASE}/ncbi/ar-reference`);
}

/**
 * Upload a 23andMe raw-data file and extract the AGA SNP panel.
 * @param {File} file - 23andMe raw-data .txt file
 * @returns {Promise<Parse23andMeResult>}
 */
async function upload23andMe(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/analyze/23andme-upload`, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || '23andMe upload failed');
    }

    return response.json();
}

// All functions are in global scope — no ES module export needed
// since analyze.html loads this as a plain <script> tag.
