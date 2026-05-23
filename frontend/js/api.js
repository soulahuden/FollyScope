// api.js, backend communication layer for Folliscope.
// Loaded as a plain <script> in analyze.html; functions live on the
// global scope so inline event handlers can reach them.

const API_BASE = '/api';

/**
 * Generic JSON fetch wrapper. Throws on non-2xx with the server's
 * `detail` field as the error message when available.
 */
async function fetchJSON(url, options = {}) {
    const response = await fetch(url, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }
    return response.json();
}

/** Full SNP reference database (called from analyze.html to build the table). */
async function getSNPDatabase() {
    return fetchJSON(`${API_BASE}/snp-database`);
}

/** Run the full risk analysis. */
async function analyzeRisk(requestData) {
    return fetchJSON(`${API_BASE}/analyze`, {
        method: 'POST',
        body: JSON.stringify(requestData),
    });
}

/** Load a pre-built sample FASTA from the static /sample_data route. */
async function loadSampleFasta(profile) {
    const response = await fetch(`/sample_data/${profile}_sample.fasta`);
    if (!response.ok) {
        throw new Error(`Could not load sample FASTA for profile "${profile}"`);
    }
    return response.text();
}

/** Upload a 23andMe raw-data file and extract the AGA SNP panel. */
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
