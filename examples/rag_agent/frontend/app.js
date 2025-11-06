// Configuration
// Auto-detect backend URL based on current hostname
// If running on same server, use same hostname; otherwise allow configuration
const getBackendUrl = () => {
    const hostname = window.location.hostname;
    // If localhost, use localhost for backend
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return 'http://localhost:5000';
    }
    // Otherwise use the same hostname with port 5000
    return `http://${hostname}:5000`;
};

const API_BASE_URL = getBackendUrl();
console.log('🔗 Backend URL:', API_BASE_URL);

// DOM Elements
const queryForm = document.getElementById('queryForm');
const submitBtn = document.getElementById('submitBtn');
const streamBtn = document.getElementById('streamBtn');
const clearBtn = document.getElementById('clearBtn');
const chatContainer = document.getElementById('chatContainer');
const messagesEl = document.getElementById('messages');
const metadataSection = document.getElementById('metadataSection');
const metadataContent = document.getElementById('metadataContent');
const loadingIndicator = document.getElementById('loadingIndicator');
const examplesContainer = document.getElementById('examplesContainer');
const questionInput = document.getElementById('question');

// Upload elements
const uploadForm = document.getElementById('uploadForm');
const uploadBtn = document.getElementById('uploadBtn');
const pdfFileInput = document.getElementById('pdfFile');
const dbTypeSelect = document.getElementById('dbType');
const uploadResultsSection = document.getElementById('uploadResultsSection');
const uploadResultsContent = document.getElementById('uploadResultsContent');

// Stats elements
const statsContainer = document.getElementById('statsContainer');
const refreshStatsBtn = document.getElementById('refreshStatsBtn');

// Tab elements
const tabButtons = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');

// Tab switching
tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        const targetTab = btn.getAttribute('data-tab');
        
        // Update active tab button
        tabButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        // Update active tab content
        tabContents.forEach(content => {
            content.style.display = 'none';
            content.classList.remove('active');
        });
        
        const targetContent = document.getElementById(`${targetTab}Tab`);
        if (targetContent) {
            targetContent.style.display = 'block';
            targetContent.classList.add('active');
        }
        
        // Load data when switching tabs
        if (targetTab === 'stats') {
            loadStats();
        } else if (targetTab === 'upload') {
            // Reload database types when switching to upload tab
            if (dbTypeSelect.options.length <= 1 || dbTypeSelect.innerHTML.includes('Loading') || dbTypeSelect.innerHTML.includes('Error')) {
                loadDatabaseTypes();
            }
        }
    });
});

// Markdown to HTML converter (simple version)
function markdownToHtml(markdown) {
    if (!markdown) return '';
    
    let html = markdown;
    
    // Headers
    html = html.replace(/### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/## (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/# (.*$)/gim, '<h3>$1</h3>');
    
    // Bold
    html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
    
    // Italic
    html = html.replace(/\*(.*?)\*/gim, '<em>$1</em>');
    
    // Lists
    html = html.replace(/^\* (.*$)/gim, '<li>$1</li>');
    html = html.replace(/^\d+\. (.*$)/gim, '<li>$1</li>');
    
    // Wrap consecutive <li> in <ul>
    html = html.replace(/(<li>.*<\/li>\n?)+/gim, '<ul>$&</ul>');
    
    // Paragraphs
    html = html.split('\n\n').map(para => {
        if (!para.trim().startsWith('<') && para.trim()) {
            return `<p>${para.trim()}</p>`;
        }
        return para;
    }).join('\n');
    
    return html;
}

// Load examples
async function loadExamples() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/examples`);
        const examples = await response.json();
        
        examplesContainer.innerHTML = examples.map(example => `
            <div class="example-card" onclick='fillExample(${JSON.stringify(example)})'>
                <h3>${example.name}</h3>
                <p>${example.question}</p>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load examples:', error);
    }
}

// Fill form with example
window.fillExample = function(example) {
    questionInput.value = example.question;
    
    // Scroll to form
    queryForm.scrollIntoView({ behavior: 'smooth' });
}

// Load database types
async function loadDatabaseTypes() {
    try {
        // Show loading state
        dbTypeSelect.innerHTML = '<option value="">Loading database types...</option>';
        dbTypeSelect.disabled = true;
        
        const response = await fetch(`${API_BASE_URL}/api/databases`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success && data.databases && Array.isArray(data.databases) && data.databases.length > 0) {
            // Clear and populate options
            dbTypeSelect.innerHTML = '<option value="">Select database type...</option>';
            
            data.databases.forEach(db => {
                const option = document.createElement('option');
                option.value = db.id;
                option.textContent = `${db.name} - ${db.description}`;
                dbTypeSelect.appendChild(option);
            });
            
            dbTypeSelect.disabled = false;
            console.log('Database types loaded successfully:', data.databases.length);
        } else {
            // Fallback to hardcoded options if API fails
            console.warn('API returned invalid data, using fallback options');
            dbTypeSelect.innerHTML = `
                <option value="">Select database type...</option>
                <option value="products">Product Information - Product details, specifications, and features</option>
                <option value="support">Customer Support & FAQ - Customer support information, FAQs, and guides</option>
                <option value="finance">Financial Information - Financial data, revenue, costs, and liabilities</option>
            `;
            dbTypeSelect.disabled = false;
        }
    } catch (error) {
        console.error('Failed to load database types:', error);
        // Fallback to hardcoded options
        dbTypeSelect.innerHTML = `
            <option value="">Select database type...</option>
            <option value="products">Product Information - Product details, specifications, and features</option>
            <option value="support">Customer Support & FAQ - Customer support information, FAQs, and guides</option>
            <option value="finance">Financial Information - Financial data, revenue, costs, and liabilities</option>
        `;
        dbTypeSelect.disabled = false;
        console.warn('Using fallback database types due to API error');
    }
}

// Chat helpers
function scrollChatToBottom() {
    if (messagesEl) {
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }
}

function createMessageElement(role, htmlContent) {
    const wrapper = document.createElement('div');
    wrapper.className = `message ${role}`;

    const avatar = document.createElement('div');
    avatar.className = `avatar ${role}`;
    avatar.textContent = role === 'user' ? '🙂' : '🤖';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    const content = document.createElement('div');
    content.className = 'content';
    content.innerHTML = htmlContent || '';
    bubble.appendChild(content);

    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);

    return { wrapper, content };
}

function appendMessage(role, textOrHtml, isMarkdown = true) {
    const html = isMarkdown ? markdownToHtml(textOrHtml) : textOrHtml;
    const { wrapper, content } = createMessageElement(role, html);
    messagesEl.appendChild(wrapper);
    scrollChatToBottom();
    return content; // return content element for streaming updates
}

function setLoading(isLoading) {
    loadingIndicator.style.display = isLoading ? 'block' : 'none';
    submitBtn.disabled = isLoading;
    streamBtn.disabled = isLoading;
}

// Show error
function showError(message) {
    appendMessage('assistant', `**Error:** ${message}`);
    setLoading(false);
}

// Handle regular query submission (Send)
queryForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const question = questionInput.value.trim();
    
    if (!question) {
        alert('Please enter a question');
        return;
    }
    
    // Add user message
    appendMessage('user', question, false);
    questionInput.value = '';
    autoResizeTextArea();
    setLoading(true);
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question })
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            // Show metadata if available
            if (result.source || result.database_used) {
                metadataSection.style.display = 'block';
                metadataContent.innerHTML = `
                    <div class="metadata-item">
                        <strong>Source:</strong> ${result.source || 'N/A'}
                    </div>
                    ${result.database_used ? `
                        <div class="metadata-item">
                            <strong>Database:</strong> ${result.database_used}
                        </div>
                    ` : ''}
                    ${result.num_documents ? `
                        <div class="metadata-item">
                            <strong>Documents Found:</strong> ${result.num_documents}
                        </div>
                    ` : ''}
                `;
            }
            appendMessage('assistant', result.answer || '');
        } else {
            showError(result.error || 'Failed to process query');
        }
    } catch (error) {
        showError(`Network error: ${error.message}`);
    } finally {
        setLoading(false);
    }
});

// Handle streaming query submission
streamBtn.addEventListener('click', async (e) => {
    e.preventDefault();
    
    const question = questionInput.value.trim();
    
    if (!question) {
        alert('Please enter a question');
        return;
    }
    
    // Add user message
    appendMessage('user', question, false);
    questionInput.value = '';
    autoResizeTextArea();
    metadataSection.style.display = 'none';
    loadingIndicator.style.display = 'none';
    submitBtn.disabled = true;
    streamBtn.disabled = true;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/query/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question })
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = '';
        let metadata = null;
        let assistantContentEl = appendMessage('assistant', '');
        
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.substring(6));
                        
                        if (data.type === 'metadata') {
                            metadata = data;
                            metadataSection.style.display = 'block';
                            metadataContent.innerHTML = `
                                <div class="metadata-item">
                                    <strong>Source:</strong> ${data.source || 'N/A'}
                                </div>
                                ${data.database_used ? `
                                    <div class="metadata-item">
                                        <strong>Database:</strong> ${data.database_used}
                                    </div>
                                ` : ''}
                            `;
                        } else if (data.type === 'content') {
                            fullText += data.content || '';
                            assistantContentEl.innerHTML = markdownToHtml(fullText);
                            scrollChatToBottom();
                        } else if (data.type === 'complete') {
                            // Streaming complete
                            console.log('Streaming complete');
                        } else if (data.type === 'error') {
                            showError(data.error || 'Unknown error');
                            return;
                        }
                    } catch (parseError) {
                        console.error('Failed to parse SSE data:', parseError);
                    }
                }
            }
        }
        
    } catch (error) {
        showError(`Streaming error: ${error.message}`);
    } finally {
        submitBtn.disabled = false;
        streamBtn.disabled = false;
    }
});

// Handle upload form submission
uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const file = pdfFileInput.files[0];
    const dbType = dbTypeSelect.value;
    
    if (!file) {
        alert('Please select a PDF file');
        return;
    }
    
    if (!dbType) {
        alert('Please select a database type');
        return;
    }
    
    uploadBtn.disabled = true;
    uploadBtn.textContent = 'Uploading...';
    uploadResultsSection.style.display = 'none';
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('db_type', dbType);
        
        const response = await fetch(`${API_BASE_URL}/api/upload`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        uploadResultsSection.style.display = 'block';
        
        if (response.ok && result.success) {
            uploadResultsContent.innerHTML = `
                <div class="upload-success">
                    <h3>✅ Upload Successful!</h3>
                    <p><strong>Message:</strong> ${result.message}</p>
                    <p><strong>Chunks Added:</strong> ${result.chunks_added}</p>
                    <p><strong>Database:</strong> ${result.database}</p>
                </div>
            `;
            
            // Reset form but preserve database type options
            pdfFileInput.value = '';
            dbTypeSelect.value = '';
            
            // Reload database types to ensure they're available
            loadDatabaseTypes();
            
            // Refresh stats
            loadStats();
        } else {
            uploadResultsContent.innerHTML = `
                <div class="upload-error">
                    <h3>❌ Upload Failed</h3>
                    <p>${result.error || 'Unknown error'}</p>
                </div>
            `;
        }
    } catch (error) {
        uploadResultsSection.style.display = 'block';
        uploadResultsContent.innerHTML = `
            <div class="upload-error">
                <h3>❌ Upload Error</h3>
                <p>${error.message}</p>
            </div>
        `;
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.textContent = 'Upload & Process';
    }
});

// Load statistics
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/stats`);
        const result = await response.json();
        
        if (result.success) {
            statsContainer.innerHTML = result.stats.map(stat => `
                <div class="stat-card">
                    <h3>${stat.name}</h3>
                    <p class="stat-description">${stat.description}</p>
                    <div class="stat-value">
                        <strong>Documents:</strong> ${stat.documents || 0}
                    </div>
                    <div class="stat-collection">
                        <small>Collection: ${stat.collection}</small>
                    </div>
                    ${stat.error ? `
                        <div class="stat-error">
                            <small>⚠️ ${stat.error}</small>
                        </div>
                    ` : ''}
                </div>
            `).join('');
        } else {
            statsContainer.innerHTML = `
                <div class="error-message">
                    <p>Failed to load statistics: ${result.error}</p>
                </div>
            `;
        }
    } catch (error) {
        statsContainer.innerHTML = `
            <div class="error-message">
                <p>Error loading statistics: ${error.message}</p>
            </div>
        `;
    }
}

// Refresh stats button
refreshStatsBtn.addEventListener('click', loadStats);

// Clear chat
clearBtn.addEventListener('click', () => {
    messagesEl.innerHTML = '';
    metadataSection.style.display = 'none';
    metadataContent.innerHTML = '';
});

// Auto-resize textarea like ChatGPT
function autoResizeTextArea() {
    questionInput.style.height = 'auto';
    questionInput.style.height = Math.min(questionInput.scrollHeight, 160) + 'px';
}
questionInput.addEventListener('input', autoResizeTextArea);
questionInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        submitBtn.click();
    }
});

// Check backend health on load
async function checkHealth() {
    const healthUrl = `${API_BASE_URL}/health`;
    console.log(`🔍 Checking backend health at: ${healthUrl}`);
    
    try {
        // Use a timeout to prevent hanging
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5 * 1000); // 5 second timeout
        
        const response = await fetch(healthUrl, {
            method: 'GET',
            signal: controller.signal,
            mode: 'cors', // Explicitly set CORS mode
            cache: 'no-cache', // Don't cache health checks
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        });
        
        clearTimeout(timeoutId);
        
        if (response.ok) {
            const health = await response.json();
            console.log('✅ Backend health check PASSED!');
            console.log('   Backend Status:', health.status);
            console.log('   Agent ID:', health.agent_id);
            console.log('   Server IP:', health.server_ip);
            console.log('   Client IP:', health.client_ip);
            console.log('   Full response:', health);
            
            // Update UI status indicator
            updateBackendStatus(true, 'Backend is running and accessible');
            
            // Show success message in a friendly way
            console.log('');
            console.log('═══════════════════════════════════════════════════════');
            console.log('✅ Backend is Running and Accessible!');
            console.log('═══════════════════════════════════════════════════════');
            
            return true;
        } else {
            console.error(`❌ Backend health check failed with status: ${response.status}`);
            console.error(`   Tried to connect to: ${healthUrl}`);
            console.error(`   Response status: ${response.status} ${response.statusText}`);
            
            // Try to get response text for more details
            try {
                const errorText = await response.text();
                console.error(`   Response body: ${errorText}`);
            } catch (e) {
                // Ignore if we can't read response
            }
            
            // Update UI status indicator
            updateBackendStatus(false, `Backend returned status ${response.status}`);
            
            return false;
        }
    } catch (error) {
        console.error('❌ Backend health check failed!');
        console.error(`   Tried to connect to: ${healthUrl}`);
        
        let errorMessage = 'Unknown error';
        if (error.name === 'AbortError') {
            errorMessage = 'Request timed out';
            console.error('   ⏱️ Request timed out after 5 seconds');
            console.error('   💡 Make sure the backend server is running and accessible');
        } else if (error.name === 'TypeError') {
            if (error.message.includes('fetch')) {
                errorMessage = 'Network error: Cannot connect';
                console.error('   🔌 Network error: Cannot connect to backend');
                console.error('   💡 Check if backend is running on port 5000');
                console.error('   💡 Check firewall/security group settings');
            } else {
                errorMessage = error.message;
                console.error(`   🔌 Error: ${error.message}`);
            }
        } else {
            errorMessage = error.message;
            console.error(`   🔌 Unexpected error: ${error.message}`);
        }
        
        // Update UI status indicator
        updateBackendStatus(false, errorMessage);
        
        // Show user-friendly message in console
        console.error('');
        console.error('═══════════════════════════════════════════════════════');
        console.error('⚠️  Backend Connection Issue');
        console.error('═══════════════════════════════════════════════════════');
        console.error(`Frontend URL: ${window.location.origin}`);
        console.error(`Backend URL: ${API_BASE_URL}`);
        console.error('');
        console.error('Possible solutions:');
        console.error('1. Ensure backend is running: python backend/app.py');
        console.error('2. Check if port 5000 is accessible');
        console.error('3. Verify firewall/security group allows port 5000');
        console.error('4. Check backend logs for errors');
        console.error('═══════════════════════════════════════════════════════');
        
        return false;
    }
}

// Update backend status indicator
function updateBackendStatus(isHealthy, message) {
    const statusIcon = document.getElementById('statusIcon');
    const statusText = document.getElementById('statusText');
    const backendStatus = document.getElementById('backendStatus');
    
    if (statusIcon && statusText && backendStatus) {
        if (isHealthy) {
            statusIcon.textContent = '✅';
            statusText.textContent = message || 'Backend is running';
            backendStatus.style.backgroundColor = 'rgba(76, 175, 80, 0.2)';
            backendStatus.style.color = '#4caf50';
            backendStatus.style.border = '1px solid #4caf50';
        } else {
            statusIcon.textContent = '❌';
            statusText.textContent = message || 'Backend connection failed';
            backendStatus.style.backgroundColor = 'rgba(244, 67, 54, 0.2)';
            backendStatus.style.color = '#f44336';
            backendStatus.style.border = '1px solid #f44336';
        }
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadExamples();
    loadDatabaseTypes(); // Load database types on page load
    
    // Check health with a small delay to allow page to fully load
    setTimeout(() => {
        checkHealth().then(isHealthy => {
            if (!isHealthy) {
                // Try once more after 2 seconds
                setTimeout(() => {
                    checkHealth();
                }, 2000);
            }
        });
    }, 500);
});

