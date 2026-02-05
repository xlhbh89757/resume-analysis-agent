// State
const state = {
    currentView: 'dashboard',
    candidates: [],
    jobs: [],
    loading: false
};

// Config
const API_BASE = '/api/v1';

// Polling
let pollInterval;

// DOM Elements
const contentArea = document.getElementById('contentArea');
const pageTitle = document.getElementById('pageTitle');

// Init
document.addEventListener('DOMContentLoaded', () => {
    setupNavigation();
    setupUpload();
    renderDashboard();
    startPolling();
});

function startPolling() {
    stopPolling();
    pollInterval = setInterval(() => {
        if (state.currentView === 'candidates') {
            fetchCandidates(true);
        } else if (state.currentView === 'dashboard') {
            fetchCandidates(true).then(() => {
                // Refresh dashboard stats silently
                const total = state.candidates.length;
                const pending = state.candidates.filter(c => c.status !== 'completed' && c.status !== 'failed').length;
                const completed = state.candidates.filter(c => c.status === 'completed').length;

                const cards = contentArea.querySelectorAll('.card p');
                if (cards.length >= 3) {
                    cards[0].textContent = total;
                    cards[1].textContent = completed;
                    cards[2].textContent = pending;
                }

                // Refresh activity list if it exists
                const existingList = contentArea.querySelector('.candidate-list');
                if (existingList && state.candidates.length > 0) {
                    // Simple Diff check: if first item ID changed, rerender
                    const firstId = existingList.querySelector('.candidate-item')?.getAttribute('onclick')?.match(/\d+/)?.[0];
                    if (firstId && parseInt(firstId) !== state.candidates[0].id) {
                        existingList.innerHTML = state.candidates.slice(0, 5).map(renderCandidateItem).join('');
                    } else if (!firstId) {
                        existingList.innerHTML = state.candidates.slice(0, 5).map(renderCandidateItem).join('');
                    }

                    // Or iterate and update status badges
                    state.candidates.slice(0, 5).forEach((c, index) => {
                        const item = existingList.children[index];
                        if (item) {
                            const badge = item.querySelector('.status-badge');
                            if (badge && badge.textContent !== c.status) {
                                badge.className = `status-badge status-${c.status}`;
                                badge.textContent = c.status;
                            }
                        }
                    });
                }
            });
        }
    }, 3000); // 3 seconds
}

function stopPolling() {
    if (pollInterval) clearInterval(pollInterval);
}

// Navigation
function setupNavigation() {
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            // Update active state
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            link.classList.add('active');

            // Switch view
            const view = link.dataset.view;
            state.currentView = view;

            switch (view) {
                case 'dashboard':
                    renderDashboard();
                    break;
                case 'candidates':
                    renderCandidates();
                    break;
                case 'jobs':
                    renderJobs();
                    break;
                case 'match':
                    renderMatchAnalysis();
                    break;
                case 'history':
                    renderMatchHistory();
                    break;
            }
        });
    });
}

// Upload Handling
function showUploadModal() {
    const modal = document.getElementById('uploadModal');
    modal.style.display = 'flex';
}

function hideUploadModal() {
    const modal = document.getElementById('uploadModal');
    modal.style.display = 'none';
    document.getElementById('uploadProgress').style.display = 'none';
}

function setupUpload() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');

    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length) handleFiles(files[0]);
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) handleFiles(e.target.files[0]);
    });
}

async function handleFiles(file) {
    const formData = new FormData();
    formData.append('file', file);

    document.getElementById('uploadProgress').style.display = 'block';

    try {
        const response = await fetch(`${API_BASE}/resumes/upload?auto_analyze=true`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error('Upload failed');

        const result = await response.json();

        // Wait a bit and then reload candidates if we are on that view
        setTimeout(() => {
            hideUploadModal();
            if (state.currentView === 'candidates') renderCandidates();
            if (state.currentView === 'dashboard') renderDashboard();
            alert(`简历上传成功！分析任务 ID: ${result.task_id || 'N/A'}`);
        }, 1000);

    } catch (error) {
        alert('上传失败: ' + error.message);
        document.getElementById('uploadProgress').style.display = 'none';
    }
}

// Render Functions
function renderDashboard() {
    pageTitle.textContent = '仪表盘';
    contentArea.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px;">
            <div class="card">
                <h3>总简历数</h3>
                <p style="font-size: 2rem; font-weight: 700; color: var(--primary-color);">Loading...</p>
            </div>
            <div class="card">
                <h3>已分析</h3>
                <p style="font-size: 2rem; font-weight: 700; color: var(--success-color);">Loading...</p>
            </div>
            <div class="card">
                <h3>分析中/待办</h3>
                <p style="font-size: 2rem; font-weight: 700; color: var(--warning-color);">Loading...</p>
            </div>
        </div>
        
        <div class="card" style="margin-top: 20px;">
            <h3>系统状态</h3>
            <p>API Status: <span style="color: var(--success-color);">Online</span></p>
            <p>LLM Model: DeepSeek-V3</p>
        </div>
        
        <div style="margin-top: 20px;">
            <h3>最近活动</h3>
            <div class="candidate-list">Loading...</div>
        </div>
    `;

    // Fetch stats
    fetchCandidates().then(() => {
        const total = state.candidates.length;
        const pending = state.candidates.filter(c => c.status !== 'completed' && c.status !== 'failed').length;
        const completed = state.candidates.filter(c => c.status === 'completed').length;

        const cards = contentArea.querySelectorAll('.card p');
        cards[0].textContent = total;
        cards[1].textContent = completed;
        cards[2].textContent = pending;

        const recentList = contentArea.querySelector('.candidate-list');
        recentList.innerHTML = state.candidates.slice(0, 5).map(renderCandidateItem).join('');
    });
}

function renderCandidates() {
    pageTitle.textContent = '候选人库';
    if (!contentArea.querySelector('.candidate-list')) {
        contentArea.innerHTML = `
            <div style="margin-bottom: 20px; display: flex; justify-content: flex-end;">
                 <button class="btn btn-outline" onclick="renderCandidates()"><i class="fa-solid fa-rotate"></i> 刷新</button>
            </div>
            <div class="loader" style="margin: 50px auto;"></div>
        `;
    }

    fetchCandidates().then(() => {
        const listContainer = contentArea.querySelector('.candidate-list') || contentArea;
        // Check if user is still on this page before overwriting
        if (state.currentView === 'candidates') {
            // Remove loader if exists
            const loader = contentArea.querySelector('.loader');
            if (loader) loader.remove();

            // Check if list container needs creating (if replaced by loader)
            if (!contentArea.querySelector('.candidate-list')) {
                contentArea.innerHTML = `
                    <div style="margin-bottom: 20px; display: flex; justify-content: flex-end;">
                        <button class="btn btn-outline" onclick="renderCandidates()"><i class="fa-solid fa-rotate"></i> 刷新</button>
                    </div>
                    <div class="candidate-list">
                        ${state.candidates.map(renderCandidateItem).join('')}
                    </div>
                  `;
            } else {
                contentArea.querySelector('.candidate-list').innerHTML = state.candidates.map(renderCandidateItem).join('');
            }
        }
    });
}

function renderCandidateItem(c) {
    const initials = c.name ? c.name.substring(0, 1) : '?';
    const statusClass = `status-${c.status}`;

    return `
        <div class="candidate-item" onclick="viewCandidate(${c.id})">
            <div class="candidate-avatar">${initials}</div>
            <div class="candidate-info">
                <div class="candidate-name">${c.name || '未命名候选人'}</div>
                <div class="candidate-meta">
                    ${c.current_position || '未知职位'} · ${c.years_of_experience || 0}年经验 · ${c.education_level || '未知学历'}
                </div>
            </div>
            <span class="status-badge ${statusClass}">${c.status}</span>
        </div>
    `;
}

async function viewCandidate(id) {
    // Fetch details
    try {
        const response = await fetch(`${API_BASE}/resumes/${id}`);
        const data = await response.json();

        pageTitle.textContent = '候选人详情';
        contentArea.innerHTML = `
            <div class="card">
                <button class="btn btn-outline" onclick="renderCandidates()" style="margin-bottom: 20px;">
                    <i class="fa-solid fa-arrow-left"></i> 返回列表
                </button>
                
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <h1>${data.name || 'Unknown'}</h1>
                        <p style="color: var(--text-secondary);">
                            <i class="fa-solid fa-envelope"></i> ${data.email || '-'} | 
                            <i class="fa-solid fa-phone"></i> ${data.phone || '-'}
                        </p>
                    </div>
                    <span class="status-badge status-${data.status}">${data.status}</span>
                </div>
                
                <hr style="margin: 20px 0; border: 0; border-top: 1px solid var(--border-color);">
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div>
                        <h3><i class="fa-solid fa-user-graduate"></i> 教育背景</h3>
                        <p>${data.education_level || '-'}</p>
                    </div>
                    <div>
                        <h3><i class="fa-solid fa-briefcase"></i> 工作经验</h3>
                        <p>${data.years_of_experience || 0} 年</p>
                    </div>
                </div>

                <div style="margin-top: 20px;">
                    <h3><i class="fa-solid fa-lightbulb"></i> 核心优势 (Summary)</h3>
                    <div class="markdown-body" style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                        ${marked.parse(data.summary || '暂无分析结果')}
                    </div>
                </div>

                <div style="margin-top: 20px;">
                     <h3><i class="fa-solid fa-list-check"></i> 工作经历</h3>
                     ${data.work_experiences && data.work_experiences.length > 0 ? data.work_experiences.map(exp => `
                        <div style="margin-bottom: 15px; padding-left: 15px; border-left: 2px solid var(--border-color);">
                            <h4>${exp.company_name || '公司'} - ${exp.position || '职位'}</h4>
                            <p style="font-size: 0.875rem; color: #666;">${exp.start_date || '?'} ~ ${exp.end_date || '至今'}</p>
                            <p>${exp.responsibilities || ''}</p>
                        </div>
                     `).join('') : '<p>暂无工作经历数据</p>'}
                </div>

                <div style="margin-top: 20px;">
                     <h3><i class="fa-solid fa-diagram-project"></i> 项目经验</h3>
                     ${data.project_experiences && data.project_experiences.length > 0 ? data.project_experiences.map(proj => `
                        <div style="margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                            <h4 style="margin: 0 0 8px 0;">${proj.project_name || '项目'} - ${proj.role || '成员'}</h4>
                            <p style="font-size: 0.875rem; color: #666; margin: 4px 0;">${proj.start_date || '?'} ~ ${proj.end_date || '至今'}</p>
                            <p style="margin: 8px 0;">${proj.description || ''}</p>
                            ${proj.technologies && proj.technologies.length > 0 ? `
                                <div style="margin: 8px 0;">
                                    <strong>技术栈:</strong> 
                                    ${proj.technologies.map(tech => `<span style="display: inline-block; padding: 2px 8px; margin: 2px; background: white; border-radius: 4px; font-size: 0.875rem;">${tech}</span>`).join('')}
                                </div>
                            ` : ''}
                            ${proj.achievements && proj.achievements.length > 0 ? `
                                <div style="margin: 8px 0;">
                                    <strong>项目成果:</strong>
                                    <ul style="margin: 4px 0; padding-left: 20px;">
                                        ${proj.achievements.map(ach => `<li>${ach}</li>`).join('')}
                                    </ul>
                                </div>
                            ` : ''}
                        </div>
                     `).join('') : '<p>暂无项目经验数据</p>'}
                </div>
            </div>
        `;
    } catch (e) {
        alert('Failed to load candidate details: ' + e.message);
    }
}

function renderJobs() {
    pageTitle.textContent = '职位管理';
    contentArea.innerHTML = `
        <div style="margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
            <button class="btn btn-primary" onclick="showCreateJobModal()">
                <i class="fa-solid fa-plus"></i> 创建职位
            </button>
            <button class="btn btn-outline" onclick="renderJobs()">
                <i class="fa-solid fa-rotate"></i> 刷新
            </button>
        </div>
        <div class="job-list"><div class="loader" style="margin: 50px auto;"></div></div>
    `;

    fetchJobs().then(() => {
        const listContainer = contentArea.querySelector('.job-list');
        if (state.jobs.length === 0) {
            listContainer.innerHTML = `
                <div class="card" style="text-align: center; padding: 40px;">
                    <i class="fa-solid fa-briefcase" style="font-size: 3rem; color: var(--border-color); margin-bottom: 20px;"></i>
                    <h3>暂无职位</h3>
                    <p style="color: var(--text-secondary);">点击上方"创建职位"按钮添加第一个职位</p>
                </div>
            `;
        } else {
            listContainer.innerHTML = state.jobs.map(renderJobItem).join('');
        }
    });
}

function renderJobItem(job) {
    const skillsPreview = job.required_skills.slice(0, 3).join(', ');
    return `
        <div class="candidate-item" onclick="viewJob(${job.id})">
            <div class="candidate-avatar" style="background: linear-gradient(135deg, #6366f1, #8b5cf6);">
                <i class="fa-solid fa-briefcase"></i>
            </div>
            <div class="candidate-info">
                <div class="candidate-name">${job.title}</div>
                <div class="candidate-meta">
                    ${job.department || '未指定部门'} · ${job.min_experience || 0}+ 年经验 · ${job.education_requirement || '不限学历'}
                </div>
                <div style="margin-top: 5px; font-size: 0.75rem; color: var(--text-secondary);">
                    技能要求: ${skillsPreview || '未指定'}${job.required_skills.length > 3 ? '...' : ''}
                </div>
            </div>
            <span class="status-badge status-${job.status}">${job.status}</span>
        </div>
    `;
}

async function viewJob(id) {
    try {
        const response = await fetch(`${API_BASE}/jobs/${id}`);
        const data = await response.json();

        pageTitle.textContent = '职位详情';
        contentArea.innerHTML = `
            <div class="card">
                <button class="btn btn-outline" onclick="renderJobs()" style="margin-bottom: 20px;">
                    <i class="fa-solid fa-arrow-left"></i> 返回列表
                </button>
                
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <h1>${data.title}</h1>
                        <p style="color: var(--text-secondary);">
                            <i class="fa-solid fa-building"></i> ${data.department || '未指定部门'} | 
                            <i class="fa-solid fa-location-dot"></i> ${data.location || '未指定地点'}
                        </p>
                    </div>
                    <span class="status-badge status-${data.status}">${data.status}</span>
                </div>
                
                <hr style="margin: 20px 0; border: 0; border-top: 1px solid var(--border-color);">
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div>
                        <h3><i class="fa-solid fa-clock"></i> 经验要求</h3>
                        <p>${data.min_experience || 0} - ${data.max_experience || '不限'} 年</p>
                    </div>
                    <div>
                        <h3><i class="fa-solid fa-graduation-cap"></i> 学历要求</h3>
                        <p>${data.education_requirement || '不限'}</p>
                    </div>
                </div>
                
                <div style="margin-top: 20px;">
                    <h3><i class="fa-solid fa-star"></i> 必需技能</h3>
                    <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px;">
                        ${data.required_skills.map(s => `<span class="skill-tag skill-tag-primary">${s}</span>`).join('') || '<span style="color: var(--text-secondary);">未指定</span>'}
                    </div>
                </div>
                
                <div style="margin-top: 20px;">
                    <h3><i class="fa-solid fa-thumbs-up"></i> 优先技能</h3>
                    <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px;">
                        ${data.preferred_skills.map(s => `<span class="skill-tag">${s}</span>`).join('') || '<span style="color: var(--text-secondary);">未指定</span>'}
                    </div>
                </div>
                
                <div style="margin-top: 20px;">
                    <h3><i class="fa-solid fa-file-lines"></i> 职位描述</h3>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 10px;">
                        ${data.description || '暂无描述'}
                    </div>
                </div>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid var(--border-color);">
                    <button class="btn btn-primary" onclick="startMatchWithJob(${data.id})">
                        <i class="fa-solid fa-users"></i> 匹配候选人
                    </button>
                </div>
            </div>
        `;
    } catch (e) {
        alert('加载职位详情失败: ' + e.message);
    }
}

function showCreateJobModal() {
    const modal = document.getElementById('uploadModal');
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 800px;">
            <div class="modal-header">
                <h2>创建职位</h2>
                <button class="close-btn" onclick="hideUploadModal()">&times;</button>
            </div>
            
            <!-- 智能填充区域 -->
            <div style="margin-bottom: 20px; padding: 15px; background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); border-radius: 12px; border: 1px solid #93c5fd;">
                <h3 style="margin: 0 0 10px 0; display: flex; align-items: center; gap: 8px;">
                    <i class="fa-solid fa-wand-magic-sparkles" style="color: var(--primary-color);"></i>
                    <span>AI 智能填充</span>
                </h3>
                <p style="font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 10px;">
                    粘贴完整的职位描述 (JD)，AI 将自动为您提取信息并填入下方表单
                </p>
                <textarea id="jdPasteArea" rows="4" placeholder="在此粘贴职位描述文本，例如：&#10;&#10;招聘 Python 后端工程师&#10;技术部 | 北京 | 3-5年经验 | 本科及以上&#10;&#10;岗位职责：&#10;1. 负责后端系统开发...&#10;&#10;任职要求：&#10;1. 熟练掌握 Python、FastAPI&#10;2. 熟悉 PostgreSQL、Redis..."
                          style="width: 100%; padding: 12px; border: 1px solid #93c5fd; border-radius: 8px; font-size: 0.875rem; font-family: inherit;"></textarea>
                <div style="margin-top: 10px; text-align: right;">
                    <button type="button" class="btn btn-primary" onclick="parseJDText(this)" style="background: linear-gradient(135deg, var(--primary-color), var(--primary-hover));">
                        <i class="fa-solid fa-bolt"></i> 自动提取信息
                    </button>
                </div>
            </div>

            <form id="createJobForm" onsubmit="submitCreateJob(event)">
                <div style="display: grid; gap: 15px;">
                    <div>
                        <label style="font-weight: 600;">职位名称 *</label>
                        <input type="text" name="title" required placeholder="例如：Python 后端工程师" 
                               style="width: 100%; padding: 10px; border: 1px solid var(--border-color); border-radius: 8px; margin-top: 5px;">
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div>
                            <label style="font-weight: 600;">部门</label>
                            <input type="text" name="department" placeholder="例如：技术部"
                                   style="width: 100%; padding: 10px; border: 1px solid var(--border-color); border-radius: 8px; margin-top: 5px;">
                        </div>
                        <div>
                            <label style="font-weight: 600;">工作地点</label>
                            <input type="text" name="location" placeholder="例如：北京"
                                   style="width: 100%; padding: 10px; border: 1px solid var(--border-color); border-radius: 8px; margin-top: 5px;">
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px;">
                        <div>
                            <label style="font-weight: 600;">最低经验(年)</label>
                            <input type="number" name="min_experience" min="0" placeholder="0"
                                   style="width: 100%; padding: 10px; border: 1px solid var(--border-color); border-radius: 8px; margin-top: 5px;">
                        </div>
                        <div>
                            <label style="font-weight: 600;">最高经验(年)</label>
                            <input type="number" name="max_experience" min="0" placeholder="10"
                                   style="width: 100%; padding: 10px; border: 1px solid var(--border-color); border-radius: 8px; margin-top: 5px;">
                        </div>
                        <div>
                            <label style="font-weight: 600;">学历要求</label>
                            <select name="education_requirement" 
                                    style="width: 100%; padding: 10px; border: 1px solid var(--border-color); border-radius: 8px; margin-top: 5px;">
                                <option value="">不限</option>
                                <option value="大专">大专</option>
                                <option value="本科">本科</option>
                                <option value="硕士">硕士</option>
                                <option value="博士">博士</option>
                            </select>
                        </div>
                    </div>
                    <div>
                        <label style="font-weight: 600;">必需技能 (逗号分隔)</label>
                        <input type="text" name="required_skills" placeholder="Python, FastAPI, PostgreSQL"
                               style="width: 100%; padding: 10px; border: 1px solid var(--border-color); border-radius: 8px; margin-top: 5px;">
                    </div>
                    <div>
                        <label style="font-weight: 600;">优先技能 (逗号分隔)</label>
                        <input type="text" name="preferred_skills" placeholder="Docker, Kubernetes, Redis"
                               style="width: 100%; padding: 10px; border: 1px solid var(--border-color); border-radius: 8px; margin-top: 5px;">
                    </div>
                    <div>
                        <label style="font-weight: 600;">职位描述</label>
                        <textarea name="description" rows="4" placeholder="详细描述岗位职责和要求..."
                                  style="width: 100%; padding: 10px; border: 1px solid var(--border-color); border-radius: 8px; margin-top: 5px; resize: vertical;"></textarea>
                    </div>
                </div>
                <div style="margin-top: 20px; display: flex; gap: 10px; justify-content: flex-end;">
                    <button type="button" class="btn btn-outline" onclick="hideUploadModal()">取消</button>
                    <button type="submit" class="btn btn-primary">创建职位</button>
                </div>
            </form>
        </div>
    `;
    modal.style.display = 'flex';
}

async function parseJDText(btn) {
    const text = document.getElementById('jdPasteArea').value.trim();
    if (!text) {
        alert('请先粘贴 JD 文本');
        return;
    }

    // UI state
    const originalHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> AI 提取中...';

    try {
        const response = await fetch(`${API_BASE}/jobs/parse`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '解析失败');
        }

        const data = await response.json();

        // Auto fill form fields
        const form = document.getElementById('createJobForm');
        if (data.title) form.querySelector('[name="title"]').value = data.title;
        if (data.department) form.querySelector('[name="department"]').value = data.department;
        if (data.location) form.querySelector('[name="location"]').value = data.location;
        if (data.min_experience !== null && data.min_experience !== undefined) {
            form.querySelector('[name="min_experience"]').value = data.min_experience;
        }
        if (data.max_experience !== null && data.max_experience !== undefined) {
            form.querySelector('[name="max_experience"]').value = data.max_experience;
        }

        // Handle skills (array to comma-separated string)
        if (data.required_skills && Array.isArray(data.required_skills)) {
            form.querySelector('[name="required_skills"]').value = data.required_skills.join(', ');
        }
        if (data.preferred_skills && Array.isArray(data.preferred_skills)) {
            form.querySelector('[name="preferred_skills"]').value = data.preferred_skills.join(', ');
        }

        // Handle education requirement dropdown
        if (data.education_requirement) {
            const select = form.querySelector('[name="education_requirement"]');
            const eduValue = data.education_requirement;
            // Try to find matching option
            for (let i = 0; i < select.options.length; i++) {
                if (select.options[i].value === eduValue ||
                    eduValue.includes(select.options[i].value)) {
                    select.selectedIndex = i;
                    break;
                }
            }
        }

        // Fill description
        if (data.description) {
            form.querySelector('[name="description"]').value = data.description;
        }

        // Show success feedback
        btn.innerHTML = '<i class="fa-solid fa-check"></i> 提取成功！';
        btn.style.background = 'linear-gradient(135deg, #10b981, #059669)';
        setTimeout(() => {
            btn.innerHTML = originalHTML;
            btn.style.background = '';
        }, 2000);

    } catch (e) {
        alert('AI 智能提取失败: ' + e.message);
        btn.innerHTML = originalHTML;
    } finally {
        btn.disabled = false;
    }
}

async function submitCreateJob(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);

    const jobData = {
        title: formData.get('title'),
        department: formData.get('department') || null,
        location: formData.get('location') || null,
        min_experience: formData.get('min_experience') ? parseInt(formData.get('min_experience')) : null,
        max_experience: formData.get('max_experience') ? parseInt(formData.get('max_experience')) : null,
        education_requirement: formData.get('education_requirement') || null,
        required_skills: formData.get('required_skills') ? formData.get('required_skills').split(',').map(s => s.trim()).filter(s => s) : [],
        preferred_skills: formData.get('preferred_skills') ? formData.get('preferred_skills').split(',').map(s => s.trim()).filter(s => s) : [],
        description: formData.get('description') || null,
    };

    try {
        const response = await fetch(`${API_BASE}/jobs/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(jobData)
        });

        if (!response.ok) throw new Error('创建失败');

        hideUploadModal();
        renderJobs();
        alert('职位创建成功！');
    } catch (e) {
        alert('创建职位失败: ' + e.message);
    }
}

function renderMatchAnalysis() {
    pageTitle.textContent = '匹配分析';
    contentArea.innerHTML = `
        <div class="card">
            <h3><i class="fa-solid fa-wand-magic-sparkles"></i> AI 智能匹配</h3>
            <p style="color: var(--text-secondary); margin-bottom: 20px;">选择一个候选人和一个职位，使用 AI 进行深度匹配分析</p>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <label style="font-weight: 600; display: block; margin-bottom: 10px;">选择候选人</label>
                    <select id="matchCandidateSelect" style="width: 100%; padding: 12px; border: 1px solid var(--border-color); border-radius: 8px;">
                        <option value="">-- 加载中 --</option>
                    </select>
                </div>
                <div>
                    <label style="font-weight: 600; display: block; margin-bottom: 10px;">选择职位</label>
                    <select id="matchJobSelect" style="width: 100%; padding: 12px; border: 1px solid var(--border-color); border-radius: 8px;">
                        <option value="">-- 加载中 --</option>
                    </select>
                </div>
            </div>
            
            <div style="margin-top: 20px;">
                <button class="btn btn-primary" onclick="runMatchAnalysis()" id="runMatchBtn">
                    <i class="fa-solid fa-brain"></i> 开始分析
                </button>
            </div>
        </div>
        
        <div id="matchResultArea" style="margin-top: 20px;"></div>
    `;

    // 加载候选人和职位列表
    Promise.all([fetchCandidates(), fetchJobs()]).then(() => {
        const candidateSelect = document.getElementById('matchCandidateSelect');
        const jobSelect = document.getElementById('matchJobSelect');

        const completedCandidates = state.candidates.filter(c => c.status === 'completed');
        candidateSelect.innerHTML = completedCandidates.length > 0
            ? `<option value="">-- 请选择候选人 --</option>` + completedCandidates.map(c =>
                `<option value="${c.id}">${c.name || '未命名'} - ${c.current_position || '未知职位'}</option>`
            ).join('')
            : `<option value="">-- 暂无已分析的候选人 --</option>`;

        jobSelect.innerHTML = state.jobs.length > 0
            ? `<option value="">-- 请选择职位 --</option>` + state.jobs.map(j =>
                `<option value="${j.id}">${j.title} - ${j.department || '未指定部门'}</option>`
            ).join('')
            : `<option value="">-- 暂无职位，请先创建 --</option>`;
    });
}

function startMatchWithJob(jobId) {
    state.currentView = 'match';
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    document.querySelector('[data-view="match"]')?.classList.add('active');
    renderMatchAnalysis();

    // 等待加载完成后预选职位
    setTimeout(() => {
        const jobSelect = document.getElementById('matchJobSelect');
        if (jobSelect) jobSelect.value = jobId;
    }, 500);
}

async function runMatchAnalysis() {
    const candidateId = document.getElementById('matchCandidateSelect').value;
    const jobId = document.getElementById('matchJobSelect').value;

    if (!candidateId || !jobId) {
        alert('请选择候选人和职位');
        return;
    }

    const btn = document.getElementById('runMatchBtn');
    const resultArea = document.getElementById('matchResultArea');

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 分析中...';
    resultArea.innerHTML = `
        <div class="card" style="text-align: center;">
            <div class="loader" style="margin: 20px auto;"></div>
            <p>AI 正在分析匹配度，请稍候...</p>
        </div>
    `;

    try {
        const response = await fetch(`${API_BASE}/match/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ candidate_id: parseInt(candidateId), job_id: parseInt(jobId) })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '分析失败');
        }

        const result = await response.json();
        renderMatchResult(result);

    } catch (e) {
        resultArea.innerHTML = `
            <div class="card" style="background: #fff5f5; border: 1px solid #feb2b2;">
                <h3 style="color: #c53030;"><i class="fa-solid fa-circle-exclamation"></i> 分析失败</h3>
                <p>${e.message}</p>
            </div>
        `;
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-brain"></i> 开始分析';
    }
}

function renderMatchResult(result) {
    const resultArea = document.getElementById('matchResultArea');
    const scoreClass = result.overall_score >= 70 ? 'success' : result.overall_score >= 50 ? 'warning' : 'danger';

    resultArea.innerHTML = `
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 20px;">
                <h2><i class="fa-solid fa-chart-pie"></i> 匹配分析结果</h2>
                <div style="text-align: center; background: linear-gradient(135deg, ${scoreClass === 'success' ? '#10b981, #059669' : scoreClass === 'warning' ? '#f59e0b, #d97706' : '#ef4444, #dc2626'}); color: white; padding: 15px 25px; border-radius: 12px;">
                    <div style="font-size: 2rem; font-weight: 700;">${result.overall_score?.toFixed(0) || 'N/A'}</div>
                    <div style="font-size: 0.75rem; opacity: 0.9;">总体匹配度</div>
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 20px;">
                <div class="card" style="text-align: center; padding: 15px;">
                    <div style="font-size: 1.5rem; font-weight: 700; color: var(--primary-color);">${result.skill_match_score?.toFixed(0) || 'N/A'}</div>
                    <div style="font-size: 0.875rem; color: var(--text-secondary);">技能匹配</div>
                </div>
                <div class="card" style="text-align: center; padding: 15px;">
                    <div style="font-size: 1.5rem; font-weight: 700; color: var(--primary-color);">${result.experience_match_score?.toFixed(0) || 'N/A'}</div>
                    <div style="font-size: 0.875rem; color: var(--text-secondary);">经验匹配</div>
                </div>
                <div class="card" style="text-align: center; padding: 15px;">
                    <div style="font-size: 1.5rem; font-weight: 700; color: var(--primary-color);">${result.education_match_score?.toFixed(0) || 'N/A'}</div>
                    <div style="font-size: 0.875rem; color: var(--text-secondary);">学历匹配</div>
                </div>
            </div>
            
            <div style="margin-top: 20px;">
                <h3><i class="fa-solid fa-lightbulb"></i> AI 总结</h3>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 10px;">
                    ${result.summary || '暂无总结'}
                </div>
            </div>
            
            <div style="margin-top: 20px;">
                <h3><i class="fa-solid fa-thumbs-up"></i> 推荐意见</h3>
                <div style="background: #f0fdf4; padding: 15px; border-radius: 8px; margin-top: 10px; border-left: 4px solid var(--success-color);">
                    ${result.recommendation || '暂无推荐意见'}
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;">
                <div>
                    <h3 style="color: var(--success-color);"><i class="fa-solid fa-check"></i> 匹配技能</h3>
                    <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px;">
                        ${result.matched_skills.map(s => `<span class="skill-tag skill-tag-primary">${s}</span>`).join('') || '<span style="color: var(--text-secondary);">无</span>'}
                    </div>
                </div>
                <div>
                    <h3 style="color: var(--warning-color);"><i class="fa-solid fa-xmark"></i> 缺失技能</h3>
                    <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px;">
                        ${result.missing_skills.map(s => `<span class="skill-tag" style="background: #fff7ed; color: #c2410c;">${s}</span>`).join('') || '<span style="color: var(--text-secondary);">无</span>'}
                    </div>
                </div>
            </div>
            
            ${result.risk_flags && result.risk_flags.length > 0 ? `
                <div style="margin-top: 20px;">
                    <h3 style="color: #dc2626;"><i class="fa-solid fa-triangle-exclamation"></i> 风险提示</h3>
                    <div style="background: #fef2f2; padding: 15px; border-radius: 8px; margin-top: 10px;">
                        <ul style="margin: 0; padding-left: 20px;">
                            ${result.risk_flags.map(r => `<li>${r}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            ` : ''}
            
            ${result.interview_questions && result.interview_questions.length > 0 ? `
                <div style="margin-top: 20px;">
                    <h3><i class="fa-solid fa-comments"></i> 建议面试问题</h3>
                    <div style="background: #eff6ff; padding: 15px; border-radius: 8px; margin-top: 10px;">
                        <ol style="margin: 0; padding-left: 20px;">
                            ${result.interview_questions.map(q => `<li style="margin-bottom: 8px;">${q}</li>`).join('')}
                        </ol>
                    </div>
                </div>
            ` : ''}
        </div>
    `;
}

// API Helpers
async function fetchCandidates(silent = false) {
    try {
        const response = await fetch(`${API_BASE}/resumes/`);
        const data = await response.json();
        state.candidates = data.items;
    } catch (e) {
        if (!silent) console.error(e);
        state.candidates = [];
    }
}

async function fetchJobs(silent = false) {
    try {
        const response = await fetch(`${API_BASE}/jobs/`);
        const data = await response.json();
        state.jobs = data;
    } catch (e) {
        if (!silent) console.error(e);
        state.jobs = [];
    }
}

// ==================== 匹配记录功能 ====================

// State for match history
state.matchHistory = [];
state.matchHistoryPage = 1;
state.matchHistoryTotal = 0;
state.matchHistoryTotalPages = 0;
state.matchHistoryJobFilter = null;

async function fetchMatchHistory(page = 1, jobId = null) {
    try {
        let url = `${API_BASE}/match/history?page=${page}&page_size=10`;
        if (jobId) url += `&job_id=${jobId}`;

        const response = await fetch(url);
        const data = await response.json();

        state.matchHistory = data.items;
        state.matchHistoryPage = data.page;
        state.matchHistoryTotal = data.total;
        state.matchHistoryTotalPages = data.total_pages;
        return data;
    } catch (e) {
        console.error('Failed to fetch match history:', e);
        state.matchHistory = [];
        return null;
    }
}

function renderMatchHistory() {
    pageTitle.textContent = '匹配记录';
    state.currentView = 'history';

    contentArea.innerHTML = `
        <div class="card" style="margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;">
                <div style="display: flex; align-items: center; gap: 15px;">
                    <h3 style="margin: 0;"><i class="fa-solid fa-clock-rotate-left"></i> 分析历史记录</h3>
                    <select id="historyJobFilter" style="padding: 8px 12px; border: 1px solid var(--border-color); border-radius: 8px; min-width: 200px;">
                        <option value="">全部职位</option>
                    </select>
                </div>
                <button class="btn btn-outline" onclick="renderMatchHistory()">
                    <i class="fa-solid fa-rotate"></i> 刷新
                </button>
            </div>
        </div>
        
        <div id="historyListArea">
            <div class="loader" style="margin: 50px auto;"></div>
        </div>
        
        <div id="historyPagination" style="margin-top: 20px; display: flex; justify-content: center; gap: 10px;"></div>
    `;

    // Load jobs for filter
    fetchJobs().then(() => {
        const select = document.getElementById('historyJobFilter');
        if (select && state.jobs.length > 0) {
            select.innerHTML = `<option value="">全部职位</option>` +
                state.jobs.map(j => `<option value="${j.id}">${j.title}</option>`).join('');
            if (state.matchHistoryJobFilter) {
                select.value = state.matchHistoryJobFilter;
            }
        }
        select.addEventListener('change', (e) => {
            state.matchHistoryJobFilter = e.target.value || null;
            state.matchHistoryPage = 1;
            loadMatchHistoryList();
        });
    });

    // Load history
    loadMatchHistoryList();
}

function loadMatchHistoryList() {
    const listArea = document.getElementById('historyListArea');
    listArea.innerHTML = '<div class="loader" style="margin: 50px auto;"></div>';

    fetchMatchHistory(state.matchHistoryPage, state.matchHistoryJobFilter).then((data) => {
        if (!data || state.matchHistory.length === 0) {
            listArea.innerHTML = `
                <div class="card" style="text-align: center; padding: 40px;">
                    <i class="fa-solid fa-inbox" style="font-size: 3rem; color: var(--border-color); margin-bottom: 20px;"></i>
                    <h3>暂无匹配记录</h3>
                    <p style="color: var(--text-secondary);">进行一次匹配分析后，记录将显示在这里</p>
                    <button class="btn btn-primary" onclick="document.querySelector('[data-view=match]').click()" style="margin-top: 15px;">
                        <i class="fa-solid fa-plus"></i> 开始匹配分析
                    </button>
                </div>
            `;
            document.getElementById('historyPagination').innerHTML = '';
            return;
        }

        listArea.innerHTML = state.matchHistory.map(renderMatchHistoryItem).join('');
        renderHistoryPagination();
    });
}

function renderMatchHistoryItem(item) {
    const scoreColor = item.overall_score >= 70 ? 'var(--success-color)' :
        item.overall_score >= 50 ? 'var(--warning-color)' : '#ef4444';
    const scoreClass = item.overall_score >= 70 ? 'success' :
        item.overall_score >= 50 ? 'warning' : 'danger';

    const date = new Date(item.created_at);
    const dateStr = date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });

    return `
        <div class="candidate-item" onclick="viewMatchHistoryDetail(${item.match_id})" style="margin-bottom: 12px;">
            <div style="display: flex; align-items: center; flex: 1; gap: 15px;">
                <div style="width: 60px; height: 60px; border-radius: 12px; background: linear-gradient(135deg, ${scoreColor}, ${scoreColor}dd); display: flex; flex-direction: column; align-items: center; justify-content: center; color: white;">
                    <div style="font-size: 1.25rem; font-weight: 700;">${item.overall_score?.toFixed(0) || 'N/A'}</div>
                    <div style="font-size: 0.625rem; opacity: 0.9;">匹配度</div>
                </div>
                <div style="flex: 1;">
                    <div style="font-weight: 600; font-size: 1rem; margin-bottom: 4px;">
                        ${item.candidate_name || '未知候选人'}
                    </div>
                    <div style="font-size: 0.875rem; color: var(--text-secondary);">
                        <i class="fa-solid fa-briefcase"></i> ${item.job_title || '未知职位'}
                    </div>
                    <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 4px;">
                        <i class="fa-regular fa-clock"></i> ${dateStr}
                        ${item.llm_provider ? `<span style="margin-left: 10px;"><i class="fa-solid fa-robot"></i> ${item.llm_provider}</span>` : ''}
                    </div>
                </div>
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
                <div style="text-align: center; padding: 5px 10px; background: #f8f9fa; border-radius: 8px; min-width: 50px;">
                    <div style="font-size: 0.875rem; font-weight: 600; color: var(--primary-color);">${item.skill_match_score?.toFixed(0) || '-'}</div>
                    <div style="font-size: 0.625rem; color: var(--text-secondary);">技能</div>
                </div>
                <div style="text-align: center; padding: 5px 10px; background: #f8f9fa; border-radius: 8px; min-width: 50px;">
                    <div style="font-size: 0.875rem; font-weight: 600; color: var(--primary-color);">${item.experience_match_score?.toFixed(0) || '-'}</div>
                    <div style="font-size: 0.625rem; color: var(--text-secondary);">经验</div>
                </div>
                <div style="text-align: center; padding: 5px 10px; background: #f8f9fa; border-radius: 8px; min-width: 50px;">
                    <div style="font-size: 0.875rem; font-weight: 600; color: var(--primary-color);">${item.education_match_score?.toFixed(0) || '-'}</div>
                    <div style="font-size: 0.625rem; color: var(--text-secondary);">学历</div>
                </div>
                <i class="fa-solid fa-chevron-right" style="color: var(--text-secondary); margin-left: 10px;"></i>
            </div>
        </div>
    `;
}

function renderHistoryPagination() {
    const paginationArea = document.getElementById('historyPagination');
    if (state.matchHistoryTotalPages <= 1) {
        paginationArea.innerHTML = '';
        return;
    }

    let html = '';

    // Previous button
    html += `<button class="btn btn-outline" ${state.matchHistoryPage <= 1 ? 'disabled' : ''} onclick="goToHistoryPage(${state.matchHistoryPage - 1})">
        <i class="fa-solid fa-chevron-left"></i>
    </button>`;

    // Page info
    html += `<span style="padding: 8px 15px; color: var(--text-secondary);">
        第 ${state.matchHistoryPage} / ${state.matchHistoryTotalPages} 页 (共 ${state.matchHistoryTotal} 条)
    </span>`;

    // Next button
    html += `<button class="btn btn-outline" ${state.matchHistoryPage >= state.matchHistoryTotalPages ? 'disabled' : ''} onclick="goToHistoryPage(${state.matchHistoryPage + 1})">
        <i class="fa-solid fa-chevron-right"></i>
    </button>`;

    paginationArea.innerHTML = html;
}

function goToHistoryPage(page) {
    if (page < 1 || page > state.matchHistoryTotalPages) return;
    state.matchHistoryPage = page;
    loadMatchHistoryList();
}

async function viewMatchHistoryDetail(matchId) {
    // Show loading modal
    const modal = document.getElementById('uploadModal');
    modal.innerHTML = `
        <div class="card" style="width: 700px; max-width: 95%; max-height: 90vh; overflow-y: auto;">
            <div class="loader" style="margin: 50px auto;"></div>
        </div>
    `;
    modal.style.display = 'flex';

    try {
        const response = await fetch(`${API_BASE}/match/${matchId}`);
        if (!response.ok) throw new Error('Failed to load match detail');
        const result = await response.json();

        const scoreClass = result.overall_score >= 70 ? 'success' : result.overall_score >= 50 ? 'warning' : 'danger';
        const scoreColor = scoreClass === 'success' ? '#10b981, #059669' : scoreClass === 'warning' ? '#f59e0b, #d97706' : '#ef4444, #dc2626';

        modal.innerHTML = `
            <div class="card" style="width: 700px; max-width: 95%; max-height: 90vh; overflow-y: auto;">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 20px;">
                    <h2 style="margin: 0;"><i class="fa-solid fa-chart-pie"></i> 匹配详情</h2>
                    <i class="fa-solid fa-xmark" style="cursor: pointer; font-size: 1.25rem; color: var(--text-secondary);" onclick="hideUploadModal()"></i>
                </div>
                
                <div style="display: flex; gap: 20px; margin-bottom: 20px;">
                    <div style="text-align: center; background: linear-gradient(135deg, ${scoreColor}); color: white; padding: 20px 30px; border-radius: 12px;">
                        <div style="font-size: 2.5rem; font-weight: 700;">${result.overall_score?.toFixed(0) || 'N/A'}</div>
                        <div style="font-size: 0.875rem; opacity: 0.9;">总体匹配度</div>
                    </div>
                    <div style="flex: 1; display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;">
                        <div style="text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                            <div style="font-size: 1.5rem; font-weight: 700; color: var(--primary-color);">${result.skill_match_score?.toFixed(0) || 'N/A'}</div>
                            <div style="font-size: 0.75rem; color: var(--text-secondary);">技能匹配</div>
                        </div>
                        <div style="text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                            <div style="font-size: 1.5rem; font-weight: 700; color: var(--primary-color);">${result.experience_match_score?.toFixed(0) || 'N/A'}</div>
                            <div style="font-size: 0.75rem; color: var(--text-secondary);">经验匹配</div>
                        </div>
                        <div style="text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                            <div style="font-size: 1.5rem; font-weight: 700; color: var(--primary-color);">${result.education_match_score?.toFixed(0) || 'N/A'}</div>
                            <div style="font-size: 0.75rem; color: var(--text-secondary);">学历匹配</div>
                        </div>
                    </div>
                </div>
                
                <div style="margin-top: 15px;">
                    <h4><i class="fa-solid fa-lightbulb"></i> AI 总结</h4>
                    <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; font-size: 0.875rem;">
                        ${result.summary || '暂无总结'}
                    </div>
                </div>
                
                <div style="margin-top: 15px;">
                    <h4><i class="fa-solid fa-thumbs-up"></i> 推荐意见</h4>
                    <div style="background: #f0fdf4; padding: 12px; border-radius: 8px; border-left: 4px solid var(--success-color); font-size: 0.875rem;">
                        ${result.recommendation || '暂无推荐意见'}
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 15px;">
                    <div>
                        <h4 style="color: var(--success-color);"><i class="fa-solid fa-check"></i> 匹配技能</h4>
                        <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                            ${result.matched_skills.map(s => `<span class="skill-tag skill-tag-primary">${s}</span>`).join('') || '<span style="color: var(--text-secondary);">无</span>'}
                        </div>
                    </div>
                    <div>
                        <h4 style="color: var(--warning-color);"><i class="fa-solid fa-xmark"></i> 缺失技能</h4>
                        <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                            ${result.missing_skills.map(s => `<span class="skill-tag" style="background: #fff7ed; color: #c2410c;">${s}</span>`).join('') || '<span style="color: var(--text-secondary);">无</span>'}
                        </div>
                    </div>
                </div>
                
                ${result.risk_flags && result.risk_flags.length > 0 ? `
                    <div style="margin-top: 15px;">
                        <h4 style="color: #dc2626;"><i class="fa-solid fa-triangle-exclamation"></i> 风险提示</h4>
                        <div style="background: #fef2f2; padding: 12px; border-radius: 8px;">
                            <ul style="margin: 0; padding-left: 20px; font-size: 0.875rem;">
                                ${result.risk_flags.map(r => `<li>${r}</li>`).join('')}
                            </ul>
                        </div>
                    </div>
                ` : ''}
                
                ${result.interview_questions && result.interview_questions.length > 0 ? `
                    <div style="margin-top: 15px;">
                        <h4><i class="fa-solid fa-comments"></i> 建议面试问题</h4>
                        <div style="background: #eff6ff; padding: 12px; border-radius: 8px;">
                            <ol style="margin: 0; padding-left: 20px; font-size: 0.875rem;">
                                ${result.interview_questions.map(q => `<li style="margin-bottom: 6px;">${q}</li>`).join('')}
                            </ol>
                        </div>
                    </div>
                ` : ''}
                
                <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid var(--border-color); display: flex; justify-content: flex-end;">
                    <button class="btn btn-outline" onclick="hideUploadModal()">关闭</button>
                </div>
            </div>
        `;
    } catch (e) {
        modal.innerHTML = `
            <div class="card" style="width: 500px; text-align: center; padding: 40px;">
                <i class="fa-solid fa-circle-exclamation" style="font-size: 3rem; color: #ef4444; margin-bottom: 20px;"></i>
                <h3>加载失败</h3>
                <p style="color: var(--text-secondary);">${e.message}</p>
                <button class="btn btn-outline" onclick="hideUploadModal()" style="margin-top: 15px;">关闭</button>
            </div>
        `;
    }
}

