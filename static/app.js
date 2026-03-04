const app = {
    token: localStorage.getItem('token'),
    baseUrl: '',

    init() {
        if (this.token) {
            this.showDashboard();
        } else {
            this.showLogin();
        }
        this.setupEventListeners();
    },

    setupEventListeners() {
        const dropzone = document.getElementById('dropzone');
        const fileInput = document.getElementById('file-input');

        dropzone.addEventListener('click', () => fileInput.click());
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('active');
        });
        dropzone.addEventListener('dragleave', () => dropzone.classList.remove('active'));
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('active');
            const files = e.dataTransfer.files;
            if (files.length) this.uploadFile(files[0]);
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) this.uploadFile(e.target.files[0]);
        });
    },

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        const icons = {
            success: '✅',
            error: '❌',
            info: 'ℹ️'
        };

        toast.innerHTML = `
            <span>${icons[type] || '🔔'}</span>
            <span>${message}</span>
        `;

        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(20px)';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    },

    async login() {
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;

        try {
            const formData = new URLSearchParams();
            formData.append('username', email);
            formData.append('password', password);

            const response = await fetch('/auth/login', {
                method: 'POST',
                body: formData,
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
            });

            const data = await response.json();
            if (response.ok) {
                this.token = data.access_token;
                localStorage.setItem('token', this.token);
                this.showToast('Successfully signed in!', 'success');
                this.showDashboard();
            } else {
                this.showToast(data.detail || 'Login failed', 'error');
            }
        } catch (e) {
            console.error(e);
            this.showToast('Connection error', 'error');
        }
    },

    async register() {
        const email = document.getElementById('reg-email').value;
        const password = document.getElementById('reg-password').value;

        try {
            const response = await fetch('/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            if (response.ok) {
                this.showToast('Registration successful! Please login.', 'success');
                this.showLogin();
            } else {
                const data = await response.json();
                this.showToast(data.detail || 'Registration failed', 'error');
            }
        } catch (e) {
            this.showToast('Connection error', 'error');
        }
    },

    logout() {
        this.token = null;
        localStorage.removeItem('token');
        location.reload();
    },

    showLogin() {
        document.getElementById('auth-section').style.display = 'flex';
        document.getElementById('dashboard-section').style.display = 'none';
        document.getElementById('login-form').style.display = 'block';
        document.getElementById('register-form').style.display = 'none';
    },

    showRegister() {
        document.getElementById('login-form').style.display = 'none';
        document.getElementById('register-form').style.display = 'block';
    },

    showDashboard() {
        document.getElementById('auth-section').style.display = 'none';
        document.getElementById('dashboard-section').style.display = 'block';
        this.fetchDatasets();
    },

    switchTab(tab) {
        const allView = document.getElementById('all-datasets-view');
        const aiView = document.getElementById('ai-analysis-view');
        const allTab = document.getElementById('tab-all');
        const aiTab = document.getElementById('tab-ai');

        if (tab === 'all') {
            allView.style.display = 'block';
            aiView.style.display = 'none';
            allTab.style.background = 'var(--glass-heavy)';
            aiTab.style.background = 'transparent';
        } else {
            allView.style.display = 'none';
            aiView.style.display = 'block';
            allTab.style.background = 'transparent';
            aiTab.style.background = 'var(--glass-heavy)';
        }
    },

    async fetchDatasets() {
        this.renderSkeletons();
        try {
            const response = await fetch('/datasets/', {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });
            const datasets = await response.json();
            if (response.ok) {
                this.renderDatasets(datasets);
            } else if (response.status === 401) {
                this.logout();
            }
        } catch (e) {
            console.error(e);
        }
    },

    renderSkeletons() {
        const grid = document.getElementById('dataset-grid');
        const aiGrid = document.getElementById('ai-dataset-grid');
        const skeletons = Array(3).fill('<div class="dataset-card glass-morphism skeleton skeleton-card"></div>').join('');
        grid.innerHTML = skeletons;
        if (aiGrid) aiGrid.innerHTML = skeletons;
    },

    selectedAiDatasetId: null,

    renderDatasets(datasets) {
        // Main Dashboard Grid
        const grid = document.getElementById('dataset-grid');
        const count = document.getElementById('total-count');
        count.innerText = datasets.length;

        grid.innerHTML = datasets.map(d => `
            <div class="dataset-card glass-morphism fade-in">
                <h4 style="margin-bottom: 0.5rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${d.name}</h4>
                <div style="color: var(--text-muted); font-size: 0.8rem; margin-bottom: 1rem;">
                    Status: <span style="color: ${d.status === 'ready' ? 'var(--accent)' : 'orange'}">${d.status}</span>
                </div>
                <div style="display: flex; gap: 0.5rem;">
                    ${d.status === 'ready' ? `<button onclick="app.download(${d.id})" class="btn-primary" style="padding: 0.4rem 0.8rem; font-size: 0.8rem;">Download</button>` : ''}
                    <button onclick="app.viewDetails(${d.id})" class="glass-morphism" style="padding: 0.4rem 0.8rem; font-size: 0.8rem; background: var(--glass-heavy)">Details</button>
                </div>
            </div>
        `).join('');

        // AI Analysis Grid (Only Ready Datasets)
        const aiGrid = document.getElementById('ai-dataset-grid');
        const readyDatasets = datasets.filter(d => d.status === 'ready');

        if (readyDatasets.length === 0) {
            aiGrid.innerHTML = '<p style="grid-column: span 3; color: var(--text-muted); text-align: center;">No cleaned datasets available for analysis yet.</p>';
        } else {
            aiGrid.innerHTML = readyDatasets.map(d => `
                <div class="dataset-card glass-morphism fade-in ai-select-card" id="ai-card-${d.id}" onclick="app.selectForAi(${d.id})">
                    <h4 style="margin-bottom: 0.5rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${d.name}</h4>
                    <div style="color: var(--accent); font-size: 0.8rem;">Dataset Ready ✨</div>
                </div>
            `).join('');
        }
    },

    selectForAi(id) {
        // Clear previous selection
        if (this.selectedAiDatasetId) {
            const prev = document.getElementById(`ai-card-${this.selectedAiDatasetId}`);
            if (prev) prev.style.borderColor = 'var(--border-color)';
        }

        this.selectedAiDatasetId = id;
        const current = document.getElementById(`ai-card-${id}`);
        if (current) current.style.borderColor = 'var(--primary)';
    },

    async generateAIReport() {
        if (!this.selectedAiDatasetId) {
            this.showToast('Please select a dataset first from the list below.', 'info');
            return;
        }

        const btn = document.getElementById('generate-btn');
        const btnText = document.getElementById('btn-text');
        const btnIcon = document.getElementById('btn-icon');
        const resultsArea = document.getElementById('ai-results');
        const promptInput = document.getElementById('ai-prompt').value.trim();
        const finalPrompt = promptInput || "Analyze this data and make a report";

        // Loading State
        btn.disabled = true;
        btn.classList.add('pulse-ai');
        btnText.innerText = 'Analyzing Data...';
        btnIcon.innerText = '⏳';
        resultsArea.style.display = 'none';

        this.showToast('AI Model is processing your data...', 'info');

        // Simulate AI Processing Time
        setTimeout(() => {
            btn.disabled = false;
            btn.classList.remove('pulse-ai');
            btnText.innerText = 'Generate AI Report';
            btnIcon.innerText = '✨';

            this.showToast('AI Analysis Complete!', 'success');

            // Render Mock Results
            resultsArea.style.display = 'block';
            document.getElementById('generation-time').innerText = `Generated at: ${new Date().toLocaleTimeString()}`;
            document.getElementById('ai-report-content').innerHTML = `
                <p><b>Summary:</b> Based on the dataset analysis, we identified several significant trends in the provided ${finalPrompt.toLowerCase()} request.</p>
                <ul style="margin: 1rem 0; padding-left: 1.5rem;">
                    <li><b>Data Quality:</b> 98% validity rate with optimized distributions.</li>
                    <li><b>Key Insight:</b> Correlation detected between user activity and peak processing times.</li>
                    <li><b>Prediction:</b> Projected growth of 15% in dataset volume over the next quarter.</li>
                </ul>
                <p style="font-size: 0.85rem; color: var(--text-muted);"><i>Note: This is a simulated report. The full AI model integration is pending.</i></p>
            `;
            resultsArea.scrollIntoView({ behavior: 'smooth' });
        }, 2500);
    },

    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/datasets/upload', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${this.token}` },
                body: formData
            });

            if (response.ok) {
                this.fetchDatasets();
                this.showToast('Upload successful!', 'success');
            } else {
                const data = await response.json();
                this.showToast(data.detail || 'Upload failed', 'error');
            }
        } catch (e) {
            this.showToast('Upload error', 'error');
        }
    },

    async download(id) {
        try {
            const response = await fetch(`/datasets/${id}/download`, {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `dataset_${id}.csv`;
                document.body.appendChild(a);
                a.click();
                a.remove();
            } else {
                this.showToast('Download failed', 'error');
            }
        } catch (e) {
            this.showToast('Download error', 'error');
        }
    },

    currentDatasetId: null,

    async viewDetails(id) {
        this.currentDatasetId = id;
        document.getElementById('modal-overlay').style.display = 'flex';

        try {
            const response = await fetch(`/datasets/${id}`, {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });
            const dataset = await response.json();

            if (response.ok) {
                document.getElementById('modal-title').innerText = dataset.name;
                this.renderMetadata(dataset.metadata);
                this.renderLogs(dataset.logs);
            }
        } catch (e) {
            console.error(e);
        }
    },

    closeModal() {
        document.getElementById('modal-overlay').style.display = 'none';
        this.currentDatasetId = null;
    },

    renderMetadata(meta) {
        const container = document.getElementById('metadata-display');
        if (!meta) {
            container.innerHTML = '<p style="grid-column: span 2; color: var(--text-muted);">No metadata available yet.</p>';
            return;
        }

        const items = [
            { label: 'Rows', value: meta.rows_count },
            { label: 'Columns', value: meta.columns_count },
            { label: 'Missing Ratio', value: (meta.missing_ratio * 100).toFixed(2) + '%' },
            { label: 'Size', value: meta.size_mb.toFixed(2) + ' MB' }
        ];

        container.innerHTML = items.map(i => `
            <div class="glass-morphism" style="padding: 1rem; border-radius: 12px;">
                <div style="color: var(--text-muted); font-size: 0.75rem;">${i.label}</div>
                <div style="font-size: 1.125rem; font-weight: 600;">${i.value}</div>
            </div>
        `).join('');
    },

    renderLogs(logs) {
        const container = document.getElementById('logs-display');
        if (!logs || logs.length === 0) {
            container.innerHTML = '<p style="padding: 1rem; color: var(--text-muted);">No logs found.</p>';
            return;
        }

        container.innerHTML = logs.map(l => `
            <div class="log-item">
                <span style="color: ${l.status === 'completed' ? 'var(--accent)' : 'var(--danger)'}">●</span>
                <b style="text-transform: capitalize;">${l.step_name}:</b> ${l.message}
            </div>
        `).join('');
    },

    async applyCleaning() {
        const drop_duplicates = document.getElementById('clean-duplicates').checked;
        const fill_missing = document.getElementById('clean-missing').value;

        try {
            const response = await fetch(`/datasets/${this.currentDatasetId}/clean`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ drop_duplicates, fill_missing })
            });

            if (response.ok) {
                this.showToast('Dataset cleaning applied successfully!', 'success');
                this.viewDetails(this.currentDatasetId); // Refresh view
                this.fetchDatasets(); // Refresh dashboard
            } else {
                const data = await response.json();
                this.showToast(data.detail || 'Cleaning failed', 'error');
            }
        } catch (e) {
            this.showToast('Cleaning error', 'error');
        }
    }
};

window.onload = () => app.init();
