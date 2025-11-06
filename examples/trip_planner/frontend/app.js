// Configuration: hardcode backend URL (adjust if needed)
const API_BASE_URL = 'http://20.84.81.110:5000';

// DOM Elements
const tripForm = document.getElementById('tripForm');
const submitBtn = document.getElementById('submitBtn');
const streamBtn = document.getElementById('streamBtn');
const clearBtn = document.getElementById('clearBtn');
const resultsSection = document.getElementById('resultsSection');
const itineraryContent = document.getElementById('itineraryContent');
const loadingIndicator = document.getElementById('loadingIndicator');
const examplesContainer = document.getElementById('examplesContainer');

// Form inputs
const destinationInput = document.getElementById('destination');
const numDaysInput = document.getElementById('numDays');
const preferencesInput = document.getElementById('preferences');

// Load examples
async function loadExamples() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/examples`);
        const examples = await response.json();
        
        examplesContainer.innerHTML = examples.map(example => `
            <div class="example-card" onclick='fillExample(${JSON.stringify(example)})'>
                <h3>${example.name}</h3>
                <p><strong>📍 Destination:</strong> ${example.destination}</p>
                <p class="days"><strong>📅 Duration:</strong> ${example.num_days} days</p>
                <p><strong>💡 Focus:</strong> ${example.preferences.substring(0, 50)}...</p>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load examples:', error);
    }
}

// Fill form with example
window.fillExample = function(example) {
    destinationInput.value = example.destination;
    numDaysInput.value = example.num_days;
    preferencesInput.value = example.preferences;
    
    // Scroll to form
    tripForm.scrollIntoView({ behavior: 'smooth' });
}

// Show loading
function showLoading() {
    resultsSection.style.display = 'block';
    loadingIndicator.style.display = 'block';
    itineraryContent.style.display = 'none';
    submitBtn.disabled = true;
    streamBtn.disabled = true;
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Hide loading
function hideLoading() {
    loadingIndicator.style.display = 'none';
    itineraryContent.style.display = 'block';
    submitBtn.disabled = false;
    streamBtn.disabled = false;
}

// Show error
function showError(message) {
    itineraryContent.innerHTML = `
        <div style="color: #dc3545; padding: 20px; text-align: center;">
            <h3>❌ Error</h3>
            <p>${message}</p>
        </div>
    `;
    hideLoading();
}

// Format itinerary data
function formatItinerary(data) {
    if (typeof data === 'string') {
        try {
            data = JSON.parse(data);
        } catch (e) {
            return `<pre>${data}</pre>`;
        }
    }
    
    // Check if it's the success response format
    if (data.success && data.itinerary) {
        data = data.itinerary;
    }
    
    // Check if it's structured itinerary
    if (data.days && Array.isArray(data.days)) {
        let html = '';

        data.days.forEach((day, index) => {
            html += `
                <div class="day">
                    <div class="day-header">Day ${index + 1}</div>
                    <div class="events-grid">
            `;

            if (day.events && Array.isArray(day.events)) {
                day.events.forEach(event => {
                    const icon = event.type === 'Restaurant' ? '🍽️' :
                               event.type === 'Travel' ? '🚶' : '🏛️';
                    const citySuffix = event.city ? `, ${event.city}` : '';
                    const mapsQuery = encodeURIComponent(`${event.location}${citySuffix}`);
                    const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${mapsQuery}`;

                    html += `
                        <div class="event">
                            <div class="event-header">
                                <div class="event-type">${icon} ${event.type}</div>
                                <a class="maps-link" href="${mapsUrl}" target="_blank" rel="noopener noreferrer">Open in Maps ↗</a>
                            </div>
                            <div class="event-location">${event.location}${citySuffix}</div>
                            <div class="event-description">${event.description}</div>
                        </div>
                    `;
                });
            }

            html += `
                    </div>
                </div>
            `;
        });

        return html;
    }
    
    // Fallback to JSON display
    return `<pre>${JSON.stringify(data, null, 2)}</pre>`;
}

// Handle regular submission
tripForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const data = {
        destination: destinationInput.value.trim(),
        num_days: parseInt(numDaysInput.value),
        preferences: preferencesInput.value.trim(),
        remote: true,
        agent_id: 'be1eef6e-2700-4980-b808-e94b3394e747'
    };
    
    if (!data.destination) {
        alert('Please enter a destination');
        return;
    }
    
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/trip`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            itineraryContent.innerHTML = formatItinerary(result);
        } else {
            showError(result.error || 'Failed to create itinerary');
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
        destination: destinationInput.value.trim(),
        num_days: parseInt(numDaysInput.value),
        preferences: preferencesInput.value.trim(),
        remote: true,
        agent_id: 'be1eef6e-2700-4980-b808-e94b3394e747'
    };
    
    if (!data.destination) {
        alert('Please enter a destination');
        return;
    }
    
    showLoading();
    itineraryContent.innerHTML = '';
    itineraryContent.style.display = 'block';
    loadingIndicator.style.display = 'none';
    submitBtn.disabled = true;
    streamBtn.disabled = true;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/trip/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let accumulatedData = '';
        
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.substring(6));
                        if (data.content) {
                            accumulatedData += data.content;
                            itineraryContent.innerHTML = formatItinerary(accumulatedData);
                            
                            // Auto-scroll to bottom
                            itineraryContent.scrollTop = itineraryContent.scrollHeight;
                        }
                    } catch (e) {
                        console.error('Error parsing stream data:', e);
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
    itineraryContent.innerHTML = '';
});

// Removed health check to avoid blocking UI if backend URL differs

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadExamples();
});