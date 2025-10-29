// Configuration
const API_BASE_URL = 'http://localhost:5000';

// DOM Elements
const recipeForm = document.getElementById('recipeForm');
const submitBtn = document.getElementById('submitBtn');
const streamBtn = document.getElementById('streamBtn');
const clearBtn = document.getElementById('clearBtn');
const resultsSection = document.getElementById('resultsSection');
const recipeContent = document.getElementById('recipeContent');
const loadingIndicator = document.getElementById('loadingIndicator');
const examplesContainer = document.getElementById('examplesContainer');

// Elements
const ingredientsInput = document.getElementById('ingredients');
const dietaryInput = document.getElementById('dietary');
const timeLimitInput = document.getElementById('timeLimit');

// Markdown to HTML converter (simple version)
function markdownToHtml(markdown) {
    let html = markdown;
    
    // Headers
    html = html.replace(/### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/## (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/# (.*$)/gim, '<h3>$1</h3>');
    
    // Bold
    html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
    
    // Lists
    html = html.replace(/^\* (.*$)/gim, '<li>$1</li>');
    html = html.replace(/^\d+\. (.*$)/gim, '<li>$1</li>');
    
    // Wrap consecutive <li> in <ul>
    html = html.replace(/(<li>.*<\/li>\n?)+/gim, '<ul>$&</ul>');
    
    // Paragraphs
    html = html.split('\n\n').map(para => {
        if (!para.startsWith('<') && para.trim()) {
            return `<p>${para}</p>`;
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
                <p><strong>Ingredients:</strong> ${example.ingredients.substring(0, 40)}...</p>
                ${example.dietary_restrictions ? `<p><strong>Diet:</strong> ${example.dietary_restrictions}</p>` : ''}
                ${example.time_limit ? `<p><strong>Time:</strong> ${example.time_limit}</p>` : ''}
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load examples:', error);
    }
}

// Fill form with example
window.fillExample = function(example) {
    ingredientsInput.value = example.ingredients;
    dietaryInput.value = example.dietary_restrictions;
    timeLimitInput.value = example.time_limit;
    
    // Scroll to form
    recipeForm.scrollIntoView({ behavior: 'smooth' });
}

// Show loading
function showLoading() {
    resultsSection.style.display = 'block';
    loadingIndicator.style.display = 'block';
    recipeContent.style.display = 'none';
    submitBtn.disabled = true;
    streamBtn.disabled = true;
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Hide loading
function hideLoading() {
    loadingIndicator.style.display = 'none';
    recipeContent.style.display = 'block';
    submitBtn.disabled = false;
    streamBtn.disabled = false;
}

// Show error
function showError(message) {
    recipeContent.innerHTML = `
        <div style="color: #dc3545; padding: 20px; text-align: center;">
            <h3>❌ Error</h3>
            <p>${message}</p>
        </div>
    `;
    hideLoading();
}

// Handle regular submission
recipeForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const data = {
        ingredients: ingredientsInput.value.trim(),
        dietary_restrictions: dietaryInput.value.trim(),
        time_limit: timeLimitInput.value.trim()
    };
    
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/recipe`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            recipeContent.innerHTML = markdownToHtml(result.recipe);
        } else {
            showError(result.error || 'Failed to create recipe');
        }
    } catch (error) {
        showError(`Network error: ${error.message}`);
    } finally {
        hideLoading();
    }
});

// Handle streaming submission
streamBtn.addEventListener('click', async (e) => {
    e.preventDefault();
    
    const data = {
        ingredients: ingredientsInput.value.trim(),
        dietary_restrictions: dietaryInput.value.trim(),
        time_limit: timeLimitInput.value.trim()
    };
    
    if (!data.ingredients) {
        alert('Please enter ingredients');
        return;
    }
    
    showLoading();
    recipeContent.innerHTML = '';
    recipeContent.style.display = 'block';
    loadingIndicator.style.display = 'none';
    submitBtn.disabled = true;
    streamBtn.disabled = true;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/recipe/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = '';
        
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.substring(6));
                    if (data.content) {
                        fullText += data.content;
                        recipeContent.innerHTML = markdownToHtml(fullText);
                        
                        // Auto-scroll to bottom
                        recipeContent.scrollTop = recipeContent.scrollHeight;
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

// Clear results
clearBtn.addEventListener('click', () => {
    resultsSection.style.display = 'none';
    recipeContent.innerHTML = '';
});

// Check backend health on load
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const health = await response.json();
        console.log('Backend health:', health);
    } catch (error) {
        console.error('Backend not reachable:', error);
        alert('Warning: Backend server is not running. Please start the Flask server.');
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadExamples();
    checkHealth();
});