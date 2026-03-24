const app = {
    token: localStorage.getItem('token'),
    baseUrl: '',

    init() {
        this.initTheme();
        this.initLanguage();
        if (this.token) {
            this.showDashboard();
        } else {
            this.showLogin();
        }
        this.setupEventListeners();
    },

    initLanguage() {
        const savedLang = localStorage.getItem('language') || 'en';
        this.applyLanguage(savedLang);
        const langSelect = document.getElementById('global-lang');
        if (langSelect) langSelect.value = savedLang;
    },

    switchLanguage(lang) {
        localStorage.setItem('language', lang);
        this.applyLanguage(lang);
        // Sync with AI language select if it exists
        const aiLang = document.getElementById('ai-language');
        if (aiLang) aiLang.value = lang;
    },

    applyLanguage(lang) {
        const dir = lang === 'ar' ? 'rtl' : 'ltr';
        document.documentElement.setAttribute('dir', dir);
        document.documentElement.lang = lang;
        
        // Dynamic UI translation could go here later, 
        // for now we at least handle the layout direction.
    },

    initTheme() {
        const savedTheme = localStorage.getItem('theme') || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);
        this.updateThemeIcon(savedTheme);
    },

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        this.updateThemeIcon(newTheme);
    },

    updateThemeIcon(theme) {
        const toggleBtn = document.getElementById('theme-toggle');
        if (toggleBtn) {
            toggleBtn.innerText = theme === 'dark' ? '🌙' : '☀️';
        }
        // Refresh charts if they exist and modal is open
        if (this.activeCharts.length > 0 && document.getElementById('modal-overlay').style.display === 'flex') {
            // We can't easily re-call this.renderCharts(stats) here without cache
            // But Chart.js can handle some updates
        }
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
            console.error('Login error:', e);
            this.showToast(`Connection error during login: ${e.message || 'Server unreachable'}`, 'error');
        }
    },

    async register() {
        const username = document.getElementById('reg-username').value;
        const email = document.getElementById('reg-email').value;
        const password = document.getElementById('reg-password').value;

        try {
            const response = await fetch('/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password, username })
            });

            if (response.ok) {
                this.showToast('Registration successful! Please login.', 'success');
                this.showLogin();
            } else {
                const data = await response.json();
                this.showToast(data.detail || 'Registration failed', 'error');
            }
        } catch (e) {
            console.error('Registration error:', e);
            this.showToast(`Connection error during registration: ${e.message || 'Server unreachable'}`, 'error');
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
        
        const payload = this.parseJwt(this.token);
        const displayName = payload.username || payload.sub || 'User';
        document.getElementById('user-display').innerText = `Welcome, ${displayName}`;
        
        this.fetchDatasets();
    },

    switchTab(tab) {
        const allView = document.getElementById('all-datasets-view');
        const aiView = document.getElementById('ai-analysis-view');
        const wsView = document.getElementById('workspace-view');
        const historyView = document.getElementById('history-view');
        
        const tabs = {
            'all': document.getElementById('tab-all'),
            'workspace': document.getElementById('tab-workspace'),
            'ai': document.getElementById('tab-ai'),
            'history': document.getElementById('tab-history')
        };

        // Reset all views and tabs
        [allView, aiView, wsView, historyView].forEach(v => {
            if (v) v.style.display = 'none';
        });
        Object.values(tabs).forEach(t => {
            if (t) t.style.background = 'transparent';
        });

        // Show selected
        const currentView = tab === 'all' ? allView : 
                          (tab === 'workspace' ? wsView : 
                          (tab === 'ai' ? aiView : historyView));
        
        if (currentView) currentView.style.display = 'block';
        if (tabs[tab]) tabs[tab].style.background = 'var(--glass-heavy)';

        if (tab === 'history') {
            this.fetchActivityLogs();
        } else {
            this.fetchDatasets(); // Refresh list to ensure they appear
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
                this.datasets = datasets;
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
        const wsGrid = document.getElementById('workspace-dataset-grid');
        const skeletons = Array(3).fill('<div class="dataset-card glass-morphism skeleton skeleton-card"></div>').join('');
        grid.innerHTML = skeletons;
        if (aiGrid) aiGrid.innerHTML = skeletons;
        if (wsGrid) wsGrid.innerHTML = skeletons;
    },

    datasets: [],
    selectedAiDatasetId: null,

    renderDatasets(datasets) {
        // Main Dashboard Grid
        const grid = document.getElementById('dataset-grid');
        const count = document.getElementById('total-count');
        count.innerText = datasets.length;
        grid.innerHTML = datasets.map(d => {
            const isShared = d.permission !== 'owner';
            return `
                <div class="dataset-card glass-morphism fade-in">
                    <h4 style="margin-bottom: 0.5rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                        ${d.name} ${isShared ? `<span class="shared-badge">${d.permission}</span>` : ''}
                    </h4>
                    <div style="color: var(--text-muted); font-size: 0.8rem; margin-bottom: 1rem;">
                        Status: <span style="color: ${d.status === 'ready' ? 'var(--accent)' : 'orange'}">${d.status}</span>
                    </div>
                    <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                        ${d.status === 'ready' ? `<button onclick="app.download(${d.id})" class="btn-primary" style="padding: 0.4rem 0.8rem; font-size: 0.8rem;">Download</button>` : ''}
                        <button onclick="app.viewDetails(${d.id})" class="glass-morphism" style="padding: 0.4rem 0.8rem; font-size: 0.8rem; background: var(--glass-heavy)">Details</button>
                        ${d.permission === 'owner' ? `<button onclick="app.openShareModal(${d.id}, '${d.name}')" class="glass-morphism" style="padding: 0.4rem 0.8rem; font-size: 0.8rem; border-color: var(--accent); color: var(--accent);">Share</button>` : ''}
                    </div>
                </div>
            `;
        }).join('');

        // AI Analysis Grid (Only Ready Datasets)
        const aiGrid = document.getElementById('ai-dataset-grid');
        const readyDatasets = datasets.filter(d => d.status === 'ready');

        if (readyDatasets.length === 0) {
            aiGrid.innerHTML = '<p style="grid-column: span 3; color: var(--text-muted); text-align: center;">No cleaned datasets available for analysis yet.</p>';
        } else {
            aiGrid.innerHTML = readyDatasets.map(d => `
                <div class="dataset-card glass-morphism fade-in ai-select-card ${this.selectedAiDatasetId === d.id ? 'active' : ''}" id="ai-card-${d.id}" onclick="app.selectForAi(${d.id})">
                    <h4 style="margin-bottom: 0.5rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${d.name}</h4>
                    <div style="color: var(--accent); font-size: 0.8rem;">Dataset Ready ✨</div>
                </div>
            `).join('');
        }

        // Workspace Grid
        const wsGrid = document.getElementById('workspace-dataset-grid');
        if (wsGrid) {
            if (readyDatasets.length === 0) {
                wsGrid.innerHTML = '<p style="grid-column: span 3; color: var(--text-muted); text-align: center;">No cleaned datasets available yet.</p>';
            } else {
                wsGrid.innerHTML = readyDatasets.map(d => `
                    <div class="dataset-card glass-morphism fade-in ai-select-card ${this.currentDatasetId === d.id ? 'active' : ''}" id="ws-card-${d.id}" onclick="app.openWorkspace(${d.id})">
                        <h4 style="margin-bottom: 0.5rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${d.name}</h4>
                        <div style="color: var(--accent); font-size: 0.8rem;">Ready for Management 🛠️</div>
                    </div>
                `).join('');
            }
        }
    },

    handleSearch(query) {
        const filtered = this.datasets.filter(d => 
            d.name.toLowerCase().includes(query.toLowerCase())
        );
        this.renderDatasets(filtered);
    },

    selectForAi(id) {
        if (this.selectedAiDatasetId) {
            const prev = document.getElementById(`ai-card-${this.selectedAiDatasetId}`);
            if (prev) prev.classList.remove('active');
        }

        this.selectedAiDatasetId = id;
        const current = document.getElementById(`ai-card-${id}`);
        if (current) current.classList.add('active');
        
        // Clear previous results/charts when a new dataset is selected
        document.getElementById('ai-results').style.display = 'none';
        document.getElementById('visualization-section').style.display = 'none';
        document.getElementById('charts-container').innerHTML = '';
        
        this.showToast('Dataset selected!', 'info');
    },

    async downloadPDF() {
        if (!this.lastAiResponse) return;
        
        this.showToast('Generating PDF via Python backend...', 'info');

        try {
            const response = await fetch('/ai/export-pdf', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    markdown_text: this.lastAiResponse,
                    filename: `AI_Report_${new Date().getTime()}.pdf`
                })
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `AI_Report_${new Date().getTime()}.pdf`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                a.remove();
                this.showToast('PDF downloaded successfully!', 'success');
            } else {
                this.showToast('PDF generation failed on server', 'error');
            }
        } catch (e) {
            console.error(e);
            this.showToast('Connection error during PDF download', 'error');
        }
    },

    lastAiResponse: '',

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
        const modelName = document.getElementById('ai-model-name').value;
        const reasoning = document.getElementById('ai-reasoning').checked;
        const language = document.getElementById('ai-language').value;
        const finalPrompt = promptInput || "Analyze this data and make a report";

        btn.disabled = true;
        btn.classList.add('pulse-ai');
        btnText.innerText = 'Analyzing Data...';
        btnIcon.innerText = '⏳';
        resultsArea.style.display = 'none';

        this.showToast('AI Model is processing your data...', 'info');

        try {
            const response = await fetch('/ai/query', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    dataset_id: this.selectedAiDatasetId,
                    user_prompt: finalPrompt,
                    model_name: modelName,
                    reasoning: reasoning,
                    language: language
                })
            });

            const data = await response.json();

            btn.disabled = false;
            btn.classList.remove('pulse-ai');
            btnText.innerText = 'Run Full Custom AI Analysis';
            btnIcon.innerText = '🚀';

            if (response.ok) {
                this.showToast('AI Analysis Complete!', 'success');
                resultsArea.style.display = 'block';
                document.getElementById('generation-time').innerText = `Generated at: ${new Date().toLocaleTimeString()}`;
                
                const rawResponse = data.response;
                this.lastAiResponse = rawResponse;
                const htmlContent = marked.parse(rawResponse);
                const isArabic = (typeof language !== 'undefined' ? language : 'en') === 'ar';

                document.getElementById('ai-report-content').innerHTML = `
                    <div class="ai-report-markdown" style="direction: ${isArabic ? 'rtl' : 'ltr'}; text-align: ${isArabic ? 'right' : 'left'};">
                        ${htmlContent}
                    </div>
                `;
                resultsArea.scrollIntoView({ behavior: 'smooth' });

                // FETCH CHARTS AFTER ANALYSIS
                this.fetchDatasetStats(this.selectedAiDatasetId);
            } else {
                this.showToast(data.detail || 'AI analysis failed', 'error');
            }
        } catch (e) {
            console.error('AI Query error:', e);
            btn.disabled = false;
            btn.classList.remove('pulse-ai');
            btnText.innerText = 'Run Full Custom AI Analysis';
            btnIcon.innerText = '🚀';
            this.showToast(`Connection error during AI analysis: ${e.message}`, 'error');
        }
    },

    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        const dropzone = document.getElementById('dropzone');
        const originalText = dropzone.innerHTML;

        dropzone.classList.add('pulse-ai');
        dropzone.innerHTML = `<p style="color: var(--primary);">⏳ Uploading ${file.name}...</p>`;

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
        } finally {
            dropzone.classList.remove('pulse-ai');
            dropzone.innerHTML = originalText;
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

    async openWorkspace(id) {
        if (this.currentDatasetId) {
            const prev = document.getElementById(`ws-card-${this.currentDatasetId}`);
            if (prev) prev.classList.remove('active');
        }

        this.currentDatasetId = id;
        const current = document.getElementById(`ws-card-${id}`);
        if (current) current.classList.add('active');

        document.getElementById('workspace-actions').style.display = 'flex';
        document.getElementById('workspace-title').innerText = `Workspace: ${current.querySelector('h4').innerText}`;
        
        this.fetchDatasetPreview(id);
    },

    async fetchDatasetPreview(id) {
        const container = document.getElementById('workspace-table-container');
        container.innerHTML = '<div id="preview-loading" style="padding: 2rem; text-align: center; color: var(--text-muted);"><span class="pulse-ai">Loading data into workspace...</span></div>';

        try {
            const response = await fetch(`/datasets/${id}/preview`, {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });
            const data = await response.json();
            if (response.ok) {
                this.renderWorkspaceTable(data.columns, data.data);
            }
        } catch (e) {
            container.innerHTML = '<p style="padding: 2rem; color: var(--danger); text-align: center;">Failed to load workspace data.</p>';
        }
    },

    renderWorkspaceTable(columns, data) {
        const container = document.getElementById('workspace-table-container');
        if (data.length === 0) {
            container.innerHTML = '<p style="padding: 4rem; text-align: center;">Dataset is empty.</p>';
            return;
        }

        let html = '<table class="preview-table"><thead><tr>';
        html += columns.map(c => `<th>${c}</th>`).join('');
        html += '</tr></thead><tbody>';

        data.forEach((row, rowIndex) => {
            html += '<tr>';
            columns.forEach(col => {
                const val = row[col] === null ? '' : row[col];
                html += `<td ondblclick="app.startEdit(this, ${rowIndex}, '${col}')">${val}</td>`;
            });
            html += '</tr>';
        });

        html += '</tbody></table>';
        container.innerHTML = html;
    },

    async startEdit(td, rowIndex, colName) {
        const dataset = this.datasets.find(d => d.id === this.currentDatasetId);
        if (dataset && dataset.permission === 'view') {
            this.showToast('You only have view permission for this dataset.', 'info');
            return;
        }

        const originalValue = td.innerText;
        const input = document.createElement('input');
        input.value = originalValue;
        input.className = 'edit-input';
        
        td.innerHTML = '';
        td.appendChild(input);
        input.focus();

        const save = async () => {
            const newValue = input.value;
            if (newValue === originalValue) {
                td.innerText = originalValue;
                return;
            }

            try {
                const response = await fetch(`/datasets/${this.currentDatasetId}/update-cell`, {
                    method: 'PATCH',
                    headers: {
                        'Authorization': `Bearer ${this.token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        row_index: rowIndex,
                        column_name: colName,
                        new_value: newValue
                    })
                });

                if (response.ok) {
                    td.innerText = newValue;
                    this.showToast('Cell updated!', 'success');
                } else {
                    this.showToast('Update failed', 'error');
                    td.innerText = originalValue;
                }
            } catch (e) {
                this.showToast('Update error', 'error');
                td.innerText = originalValue;
            }
        };

        input.onblur = save;
        input.onkeydown = (e) => {
            if (e.key === 'Enter') save();
            if (e.key === 'Escape') td.innerText = originalValue;
        };
    },

    async downloadFormat(format) {
        this.showToast(`Preparing ${format.toUpperCase()}...`, 'info');
        try {
            const response = await fetch(`/datasets/${this.currentDatasetId}/download?format=${format}`, {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${document.getElementById('modal-title').innerText.split('.')[0]}.${format === 'excel' ? 'xlsx' : 'json'}`;
                a.click();
                this.showToast(`${format.toUpperCase()} downloaded!`, 'success');
            } else {
                this.showToast('Export failed', 'error');
            }
        } catch (e) {
            this.showToast('Export error', 'error');
        }
    },

    async fetchDatasetStats(id) {
        const vizSection = document.getElementById('visualization-section');
        const vizLoading = document.getElementById('viz-loading');
        vizSection.style.display = 'block';
        vizLoading.style.display = 'inline';

        try {
            const response = await fetch(`/datasets/${id}/stats`, {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });
            const stats = await response.json();
            if (response.ok) {
                this.renderCharts(stats);
            }
        } catch (e) {
            console.error('Error fetching stats:', e);
        } finally {
            vizLoading.style.display = 'none';
        }
    },

    activeCharts: [],

    renderCharts(stats) {
        try {
            // Destroy previous charts to avoid memory leaks
            if (this.activeCharts && this.activeCharts.length > 0) {
                this.activeCharts.forEach(c => c && c.destroy && c.destroy());
            }
            this.activeCharts = [];

            const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
            const textColor = isDarkMode ? '#94a3b8' : '#64748b';
            const gridColor = isDarkMode ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)';

            const formatCurrency = (val) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(val);
            const formatNumber = (val) => new Intl.NumberFormat('en-US', { notation: "compact", compactDisplay: "short" }).format(val);

            // 1. Render KPIs
            const kpis = stats?.smart_kpis || {};
            if (Object.keys(kpis).length > 0) {
                const kpiContainer = document.getElementById('kpi-container');
                if(kpiContainer) kpiContainer.style.display = 'grid';
                
                const sEl = document.getElementById('kpi-sales');
                if(sEl) sEl.innerText = kpis.total_sales ? formatCurrency(kpis.total_sales) : '-';
                
                const cEl = document.getElementById('kpi-cost');
                if(cEl) cEl.innerText = kpis.total_cost ? formatCurrency(kpis.total_cost) : '-';
                
                const pEl = document.getElementById('kpi-profit');
                if(pEl) pEl.innerText = kpis.total_profit ? formatCurrency(kpis.total_profit) : '-';
                
                const mEl = document.getElementById('kpi-margin');
                if(mEl) mEl.innerText = kpis.profit_margin ? kpis.profit_margin.toFixed(1) + '%' : '-';
            }

            const charts = stats?.smart_charts || {};
            
            // Helper to format chart data
            const createChart = (ctxId, config) => {
                const ctx = document.getElementById(ctxId);
                if(ctx) {
                    try {
                        this.activeCharts.push(new Chart(ctx.getContext('2d'), config));
                    } catch (err) {
                        console.error("Failed to render chart", ctxId, config, err);
                        this.showToast("Failed to render chart " + ctxId, "error");
                    }
                }
            };

            // Trend Chart
            if (charts.sales_trend) {
                document.querySelector('.dashboard-trend .chart-title').innerText = 'Sales & Profit Trends';
                createChart('chart-trend', {
                    type: 'line',
                    data: {
                        labels: charts.sales_trend.labels || [],
                        datasets: [
                            {
                                label: 'Sales',
                                data: charts.sales_trend.data || [],
                                borderColor: '#2563eb',
                                backgroundColor: 'rgba(37, 99, 235, 0.1)',
                                fill: true,
                                tension: 0.4
                            },
                            charts.sales_trend.profit_data ? {
                                label: 'Profit',
                                data: charts.sales_trend.profit_data,
                                borderColor: '#10b981',
                                backgroundColor: 'transparent',
                                borderDash: [5, 5],
                                tension: 0.4
                            } : null
                        ].filter(d => Boolean(d))
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { labels: { color: textColor } } },
                        scales: {
                            y: { grid: { color: gridColor }, ticks: { color: textColor, callback: (val) => formatNumber(val) } },
                            x: { grid: { display: false }, ticks: { color: textColor } }
                        }
                    }
                });
            }

            // Top Products Bar
            if (charts.top_products) {
                document.getElementById('title-bar1').innerText = 'Top Products By Sales';
                createChart('chart-bar1', {
                    type: 'bar',
                    data: {
                        labels: (charts.top_products.labels || []).map(l => l && typeof l === 'string' && l.length > 15 ? l.substring(0, 15)+'...' : l),
                        datasets: [{
                            label: 'Sales',
                            data: charts.top_products.data || [],
                            backgroundColor: '#3b82f6',
                            borderRadius: 4
                        }]
                    },
                    options: {
                        indexAxis: 'y', // Horizontal
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            x: { grid: { color: gridColor }, ticks: { color: textColor, callback: (val) => formatNumber(val) } },
                            y: { grid: { display: false }, ticks: { color: textColor } }
                        }
                    }
                });
            }

            // Donut Chart - Top Customers or first categorical
            if (charts.top_customers) {
                document.getElementById('title-donut1').innerText = 'Sales by Segment';
                createChart('chart-donut1', {
                    type: 'doughnut',
                    data: {
                        labels: (charts.top_customers.labels||[]).slice(0, 5).map(l => l && typeof l === 'string' && l.length > 15 ? l.substring(0, 15)+'...' : l),
                        datasets: [{
                            data: (charts.top_customers.data||[]).slice(0, 5),
                            backgroundColor: ['#2563eb', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899'],
                            borderWidth: 0
                        }]
                    },
                    options: {
                        responsive: true, maintainAspectRatio: false,
                        plugins: { legend: { position: 'right', labels: { color: textColor } } },
                        cutout: '70%'
                    }
                });
            }

            // Bar 2 - Suppliers or Cost
            if (charts.top_suppliers) {
                document.getElementById('title-bar2').innerText = `Top Suppliers By ${charts.top_suppliers.metric_name || 'Metric'}`;
                createChart('chart-bar2', {
                    type: 'bar',
                    data: {
                        labels: (charts.top_suppliers.labels||[]).map(l => l && typeof l === 'string' && l.length > 15 ? l.substring(0, 15)+'...' : l),
                        datasets: [{
                            label: charts.top_suppliers.metric_name || 'Data',
                            data: charts.top_suppliers.data || [],
                            backgroundColor: '#f59e0b',
                            borderRadius: 4
                        }]
                    },
                    options: {
                        indexAxis: 'y',
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            x: { grid: { color: gridColor }, ticks: { color: textColor, callback: (val) => formatNumber(val) } },
                            y: { grid: { display: false }, ticks: { color: textColor } }
                        }
                    }
                });
            }

            // --- FALLBACKS if Smart Charts are missing but stats exist ---
            if(!charts.sales_trend && stats && stats.numerical && Object.keys(stats.numerical).length > 0) {
                const first_num = Object.keys(stats.numerical)[0];
                const data = stats.numerical[first_num];
                if(data && data.histogram && data.histogram.bins && data.histogram.counts) {
                    const titleEl = document.querySelector('.dashboard-trend .chart-title');
                    if(titleEl) titleEl.innerText = `${first_num} Distribution`;
                    createChart('chart-trend', {
                         type: 'bar',
                         data: {
                             labels: data.histogram.bins.slice(0, -1).map(b => Number(b).toFixed(1)),
                             datasets: [{ label: 'Frequency', data: data.histogram.counts, backgroundColor: '#6366f1' }]
                         },
                         options: { responsive: true, maintainAspectRatio: false, scales:{y:{grid:{color:gridColor}, ticks:{color:textColor}}, x:{grid:{display:false}, ticks:{color:textColor}}} }
                    });
                }
            }
            
            if(!charts.top_customers && stats && stats.categorical && Object.keys(stats.categorical).length > 0) {
                const first_cat = Object.keys(stats.categorical)[0];
                if(stats.categorical[first_cat]) {
                    const titleEl2 = document.getElementById('title-donut1');
                    if(titleEl2) titleEl2.innerText = `${first_cat} Split`;
                    createChart('chart-donut1', {
                        type: 'doughnut',
                        data: {
                            labels: Object.keys(stats.categorical[first_cat]),
                            datasets: [{ data: Object.values(stats.categorical[first_cat]), backgroundColor: ['#2563eb', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#ef4444'], borderWidth: 0 }]
                        },
                        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right', labels: { color: textColor } } }, cutout: '70%'}
                    });
                }
            }
            
            // Hide unused cards if no data generated
            const prods = document.querySelector('.dashboard-products');
            if(prods) prods.style.display = charts.top_products ? 'flex' : 'none';
            
            const supps = document.querySelector('.dashboard-suppliers');
            if(supps) supps.style.display = charts.top_suppliers ? 'flex' : 'none';
            
        } catch (globalErr) {
            console.error(globalErr);
            alert("Crash in renderCharts: " + globalErr.toString());
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
        const ai_rename = document.getElementById('clean-ai-rename').checked;
        
        const btn = document.querySelector('.cleaning-options button');
        const originalText = btn.innerText;
        btn.disabled = true;
        btn.innerText = '✨ Processing...';

        try {
            const response = await fetch(`/datasets/${this.currentDatasetId}/clean`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ drop_duplicates, fill_missing, ai_rename })
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
        } finally {
            btn.disabled = false;
            btn.innerText = originalText;
        }
    },

    async generateAutoSummary() {
        if (!this.currentDatasetId) return;
        
        const btn = document.getElementById('btn-auto-summarize');
        const resultDiv = document.getElementById('auto-summary-result');
        
        btn.disabled = true;
        btn.innerHTML = '⏳ Processing...';
        resultDiv.style.display = 'none';

        try {
            const response = await fetch('/ai/summarize', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    dataset_id: this.currentDatasetId,
                    language: document.getElementById('ai-language')?.value || 'en'
                })
            });
            const data = await response.json();
            if (response.ok) {
                resultDiv.innerHTML = `<div class="ai-report-markdown">${marked.parse(data.response)}</div>`;
                resultDiv.style.display = 'block';
                btn.innerHTML = '🪄 Summary Generated';
            } else {
                this.showToast('Summary failed', 'error');
                btn.disabled = false;
                btn.innerHTML = '🪄 Auto-Summarize with AI';
            }
        } catch (e) {
            this.showToast('AI Error', 'error');
            btn.disabled = false;
            btn.innerHTML = '🪄 Auto-Summarize with AI';
        }
    },

    async runSpecializedAi(type) {
        if (!this.selectedAiDatasetId) {
            this.showToast('Please select a dataset first', 'info');
            return;
        }

        const btnId = type === 'analyze-anomalies' ? 'btn-anomaly' : (type === 'correlation' ? 'btn-correlation' : 'btn-forecast');
        const btn = document.getElementById(btnId);
        const originalHtml = btn.innerHTML;

        btn.disabled = true;
        btn.innerHTML = '⏳ Analyzing...';

        const resultsArea = document.getElementById('ai-results');
        const reportDiv = document.getElementById('ai-report-content');
        const vizSection = document.getElementById('visualization-section');

        resultsArea.style.display = 'block';
        reportDiv.innerHTML = '<p class="pulse-ai" style="text-align: center; padding: 2rem;">Deep AI analysis in progress...</p>';
        vizSection.style.display = 'none';

        try {
            const response = await fetch(`/ai/${type}`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    dataset_id: this.selectedAiDatasetId,
                    language: document.getElementById('ai-language').value,
                    model_name: document.getElementById('ai-model-name').value
                })
            });

            const data = await response.json();
            if (response.ok) {
                const isArabic = document.getElementById('ai-language').value === 'ar';
                reportDiv.innerHTML = `
                    <div class="ai-report-markdown" style="direction: ${isArabic ? 'rtl' : 'ltr'}; text-align: ${isArabic ? 'right' : 'left'};">
                        ${marked.parse(data.response)}
                    </div>
                `;
                resultsArea.scrollIntoView({ behavior: 'smooth' });
                this.showToast('Analysis complete!', 'success');
                this.lastAiResponse = data.response;
            } else {
                this.showToast('Analysis failed', 'error');
            }
        } catch (e) {
            this.showToast('Connection error', 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    },

    copyToClipboard() {
        if (!this.lastAiResponse) return;
        navigator.clipboard.writeText(this.lastAiResponse).then(() => {
            this.showToast('Report copied to clipboard!', 'success');
        });
    },

    async fetchActivityLogs() {
        const container = document.getElementById('activity-logs-container');
        container.innerHTML = '<p style="color: var(--text-muted); text-align: center;" class="pulse-ai">Loading activity history...</p>';

        try {
            const response = await fetch('/collaboration/history', {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });
            const logs = await response.json();
            if (response.ok) {
                if (logs.length === 0) {
                    container.innerHTML = '<p style="color: var(--text-muted); text-align: center;">No activity recorded yet.</p>';
                } else {
                    container.innerHTML = logs.map(l => `
                        <div class="glass-morphism" style="padding: 1rem; display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <b style="color: var(--accent); text-transform: uppercase; font-size: 0.75rem;">${l.action}</b>
                                <div style="font-size: 0.9rem; margin-top: 0.25rem;">${l.details || 'No details'}</div>
                            </div>
                            <div style="color: var(--text-muted); font-size: 0.75rem;">
                                ${new Date(l.timestamp).toLocaleString()}
                            </div>
                        </div>
                    `).join('');
                }
            }
        } catch (e) {
            container.innerHTML = '<p style="color: var(--danger); text-align: center;">Failed to load history.</p>';
        }
    },

    openShareModal(id, name) {
        this.currentShareDatasetId = id;
        document.getElementById('share-dataset-name').innerText = `Dataset: ${name}`;
        document.getElementById('share-modal-overlay').style.display = 'flex';
    },

    closeShareModal() {
        document.getElementById('share-modal-overlay').style.display = 'none';
        this.currentShareDatasetId = null;
    },

    async submitShare() {
        const email = document.getElementById('share-email').value;
        const permission = document.getElementById('share-permission').value;

        if (!email) {
            this.showToast('Please enter an email address', 'info');
            return;
        }

        try {
            const response = await fetch('/collaboration/share', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    dataset_id: this.currentShareDatasetId,
                    email: email,
                    permission: permission
                })
            });

            const data = await response.json();
            if (response.ok) {
                this.showToast(`Shared successfully with ${email}`, 'success');
                this.closeShareModal();
            } else {
                this.showToast(data.detail || 'Sharing failed', 'error');
            }
        } catch (e) {
            this.showToast('Sharing error', 'error');
        }
    },

    openShareModalFromDetails() {
        if (!this.currentDatasetId) return;
        const dataset = this.datasets.find(d => d.id === this.currentDatasetId);
        if (dataset) {
            this.closeModal();
            this.openShareModal(dataset.id, dataset.name);
        }
    },

    parseJwt(token) {
        try {
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
            }).join(''));
            return JSON.parse(jsonPayload);
        } catch (e) {
            return {};
        }
    }
};

window.onload = () => app.init();
