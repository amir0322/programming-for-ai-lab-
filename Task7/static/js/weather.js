// Weather App JavaScript

// API Configuration
const API_BASE_URL = 'http://localhost:5000/api';

// DOM Elements
const elements = {
    // Tab elements
    tabButtons: document.querySelectorAll('.tab-btn'),
    tabContents: document.querySelectorAll('.tab-content'),
    
    // Current weather elements
    cityInput: document.getElementById('cityInput'),
    unitsSelect: document.getElementById('unitsSelect'),
    searchBtn: document.getElementById('searchBtn'),
    weatherDisplay: document.getElementById('weatherDisplay'),
    quickCityBtns: document.querySelectorAll('.quick-city-btn'),
    
    // Coordinates elements
    latInput: document.getElementById('latInput'),
    lonInput: document.getElementById('lonInput'),
    coordUnitsSelect: document.getElementById('coordUnitsSelect'),
    coordSearchBtn: document.getElementById('coordSearchBtn'),
    coordWeatherDisplay: document.getElementById('coordWeatherDisplay'),
    quickCoordBtns: document.querySelectorAll('.quick-coord-btn'),
    
    // Forecast elements
    forecastCityInput: document.getElementById('forecastCityInput'),
    forecastUnitsSelect: document.getElementById('forecastUnitsSelect'),
    forecastSearchBtn: document.getElementById('forecastSearchBtn'),
    forecastDisplay: document.getElementById('forecastDisplay'),
    
    // UI elements
    loading: document.getElementById('loading'),
    errorDisplay: document.getElementById('errorDisplay'),
    errorMessage: document.getElementById('errorMessage'),
    retryBtn: document.getElementById('retryBtn'),
    apiModal: document.getElementById('apiModal')
};

// Initialize the app
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    checkApiHealth();
});

// Event Listeners
function initializeEventListeners() {
    // Tab switching
    elements.tabButtons.forEach(button => {
        button.addEventListener('click', () => switchTab(button.dataset.tab));
    });
    
    // Current weather search
    elements.searchBtn.addEventListener('click', searchCurrentWeather);
    elements.cityInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchCurrentWeather();
    });
    
    // Quick city buttons
    elements.quickCityBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            elements.cityInput.value = btn.dataset.city;
            searchCurrentWeather();
        });
    });
    
    // Coordinates search
    elements.coordSearchBtn.addEventListener('click', searchByCoordinates);
    [elements.latInput, elements.lonInput].forEach(input => {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') searchByCoordinates();
        });
    });
    
    // Quick coordinates buttons
    elements.quickCoordBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            elements.latInput.value = btn.dataset.lat;
            elements.lonInput.value = btn.dataset.lon;
            searchByCoordinates();
        });
    });
    
    // Forecast search
    elements.forecastSearchBtn.addEventListener('click', searchForecast);
    elements.forecastCityInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchForecast();
    });
    
    // Error retry
    elements.retryBtn.addEventListener('click', hideError);
}

// Tab Management
function switchTab(tabName) {
    // Update tab buttons
    elements.tabButtons.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    
    // Update tab content
    elements.tabContents.forEach(content => {
        content.classList.toggle('active', content.id === tabName);
    });
    
    // Hide any errors when switching tabs
    hideError();
}

// API Health Check
async function checkApiHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (!response.ok) {
            console.warn('API health check failed');
        }
    } catch (error) {
        console.warn('Could not connect to API:', error);
    }
}

// Current Weather Functions
async function searchCurrentWeather() {
    const city = elements.cityInput.value.trim();
    const units = elements.unitsSelect.value;
    
    if (!city) {
        showError('Please enter a city name');
        return;
    }
    
    showLoading();
    hideError();
    
    try {
        const response = await fetch(`${API_BASE_URL}/weather/current?city=${encodeURIComponent(city)}&units=${units}`);
        const data = await response.json();
        
        if (data.success) {
            displayCurrentWeather(data.data);
        } else {
            showError(data.error || 'Failed to fetch weather data');
        }
    } catch (error) {
        showError('Network error. Please check if the Flask server is running on http://localhost:5000');
    } finally {
        hideLoading();
    }
}

// Coordinates Weather Functions
async function searchByCoordinates() {
    const lat = elements.latInput.value.trim();
    const lon = elements.lonInput.value.trim();
    const units = elements.coordUnitsSelect.value;
    
    if (!lat || !lon) {
        showError('Please enter both latitude and longitude');
        return;
    }
    
    if (isNaN(lat) || isNaN(lon)) {
        showError('Please enter valid numeric coordinates');
        return;
    }
    
    showLoading();
    hideError();
    
    try {
        const response = await fetch(`${API_BASE_URL}/weather/coordinates?lat=${lat}&lon=${lon}&units=${units}`);
        const data = await response.json();
        
        if (data.success) {
            displayCoordinatesWeather(data.data);
        } else {
            showError(data.error || 'Failed to fetch weather data');
        }
    } catch (error) {
        showError('Network error. Please check if the Flask server is running on http://localhost:5000');
    } finally {
        hideLoading();
    }
}

// Forecast Functions
async function searchForecast() {
    const city = elements.forecastCityInput.value.trim();
    const units = elements.forecastUnitsSelect.value;
    
    if (!city) {
        showError('Please enter a city name');
        return;
    }
    
    showLoading();
    hideError();
    
    try {
        const response = await fetch(`${API_BASE_URL}/weather/forecast?city=${encodeURIComponent(city)}&units=${units}`);
        const data = await response.json();
        
        if (data.success) {
            displayForecast(data.data);
        } else {
            showError(data.error || 'Failed to fetch forecast data');
        }
    } catch (error) {
        showError('Network error. Please check if the Flask server is running on http://localhost:5000');
    } finally {
        hideLoading();
    }
}

// Display Functions
function displayCurrentWeather(weatherData) {
    const unitSymbol = getUnitSymbol(weatherData.units);
    const speedUnit = getSpeedUnit(weatherData.units);
    
    const weatherIcon = getWeatherIcon(weatherData.weather.main);
    
    const weatherCard = `
        <div class="weather-card">
            <div class="weather-header">
                <div class="location-info">
                    <h2>${weatherData.city}, ${weatherData.country}</h2>
                    <p><i class="fas fa-map-marker-alt"></i> ${weatherData.coordinates.lat.toFixed(4)}, ${weatherData.coordinates.lon.toFixed(4)}</p>
                    <p><i class="fas fa-clock"></i> ${weatherData.timestamp}</p>
                </div>
                <div class="weather-icon">
                    <i class="${weatherIcon}"></i>
                </div>
            </div>
            
            <div class="temperature-main">
                <div class="temp-current">${Math.round(weatherData.temperature.current)}°${unitSymbol}</div>
                <div class="temp-description">${weatherData.weather.description}</div>
                <div class="temp-range">
                    <span><i class="fas fa-thermometer-empty"></i> Min: ${Math.round(weatherData.temperature.min)}°${unitSymbol}</span>
                    <span><i class="fas fa-thermometer-full"></i> Max: ${Math.round(weatherData.temperature.max)}°${unitSymbol}</span>
                </div>
            </div>
            
            <div class="weather-details">
                <div class="detail-item">
                    <i class="fas fa-thermometer-half"></i>
                    <h4>Feels Like</h4>
                    <p>${Math.round(weatherData.temperature.feels_like)}°${unitSymbol}</p>
                </div>
                <div class="detail-item">
                    <i class="fas fa-tint"></i>
                    <h4>Humidity</h4>
                    <p>${weatherData.humidity}%</p>
                </div>
                <div class="detail-item">
                    <i class="fas fa-compress-arrows-alt"></i>
                    <h4>Pressure</h4>
                    <p>${weatherData.pressure} hPa</p>
                </div>
                <div class="detail-item">
                    <i class="fas fa-wind"></i>
                    <h4>Wind Speed</h4>
                    <p>${weatherData.wind.speed} ${speedUnit}</p>
                </div>
                <div class="detail-item">
                    <i class="fas fa-eye"></i>
                    <h4>Visibility</h4>
                    <p>${weatherData.visibility !== 'N/A' ? (weatherData.visibility / 1000).toFixed(1) + ' km' : 'N/A'}</p>
                </div>
                <div class="detail-item">
                    <i class="fas fa-sun"></i>
                    <h4>Sunrise</h4>
                    <p>${weatherData.sunrise}</p>
                </div>
                <div class="detail-item">
                    <i class="fas fa-moon"></i>
                    <h4>Sunset</h4>
                    <p>${weatherData.sunset}</p>
                </div>
                <div class="detail-item">
                    <i class="fas fa-compass"></i>
                    <h4>Wind Direction</h4>
                    <p>${weatherData.wind.direction !== 'N/A' ? weatherData.wind.direction + '°' : 'N/A'}</p>
                </div>
            </div>
        </div>
    `;
    
    elements.weatherDisplay.innerHTML = weatherCard;
}

function displayCoordinatesWeather(weatherData) {
    const unitSymbol = getUnitSymbol(weatherData.units);
    const speedUnit = getSpeedUnit(weatherData.units);
    const weatherIcon = getWeatherIcon(weatherData.weather.main);
    
    const weatherCard = `
        <div class="weather-card">
            <div class="weather-header">
                <div class="location-info">
                    <h2>${weatherData.city}, ${weatherData.country}</h2>
                    <p><i class="fas fa-crosshairs"></i> ${weatherData.coordinates.lat.toFixed(4)}, ${weatherData.coordinates.lon.toFixed(4)}</p>
                    <p><i class="fas fa-clock"></i> ${weatherData.timestamp}</p>
                </div>
                <div class="weather-icon">
                    <i class="${weatherIcon}"></i>
                </div>
            </div>
            
            <div class="temperature-main">
                <div class="temp-current">${Math.round(weatherData.temperature.current)}°${unitSymbol}</div>
                <div class="temp-description">${weatherData.weather.description}</div>
                <div class="temp-range">
                    <span><i class="fas fa-thermometer-empty"></i> Min: ${Math.round(weatherData.temperature.min)}°${unitSymbol}</span>
                    <span><i class="fas fa-thermometer-full"></i> Max: ${Math.round(weatherData.temperature.max)}°${unitSymbol}</span>
                </div>
            </div>
            
            <div class="weather-details">
                <div class="detail-item">
                    <i class="fas fa-thermometer-half"></i>
                    <h4>Feels Like</h4>
                    <p>${Math.round(weatherData.temperature.feels_like)}°${unitSymbol}</p>
                </div>
                <div class="detail-item">
                    <i class="fas fa-tint"></i>
                    <h4>Humidity</h4>
                    <p>${weatherData.humidity}%</p>
                </div>
                <div class="detail-item">
                    <i class="fas fa-compress-arrows-alt"></i>
                    <h4>Pressure</h4>
                    <p>${weatherData.pressure} hPa</p>
                </div>
                <div class="detail-item">
                    <i class="fas fa-wind"></i>
                    <h4>Wind Speed</h4>
                    <p>${weatherData.wind.speed} ${speedUnit}</p>
                </div>
                <div class="detail-item">
                    <i class="fas fa-eye"></i>
                    <h4>Visibility</h4>
                    <p>${weatherData.visibility !== 'N/A' ? (weatherData.visibility / 1000).toFixed(1) + ' km' : 'N/A'}</p>
                </div>
                <div class="detail-item">
                    <i class="fas fa-sun"></i>
                    <h4>Sunrise</h4>
                    <p>${weatherData.sunrise}</p>
                </div>
                <div class="detail-item">
                    <i class="fas fa-moon"></i>
                    <h4>Sunset</h4>
                    <p>${weatherData.sunset}</p>
                </div>
                <div class="detail-item">
                    <i class="fas fa-compass"></i>
                    <h4>Wind Direction</h4>
                    <p>${weatherData.wind.direction !== 'N/A' ? weatherData.wind.direction + '°' : 'N/A'}</p>
                </div>
            </div>
        </div>
    `;
    
    elements.coordWeatherDisplay.innerHTML = weatherCard;
}

function displayForecast(forecastData) {
    const unitSymbol = getUnitSymbol(forecastData.units);
    
    // Group forecast data by date
    const dailyForecasts = {};
    forecastData.forecast.forEach(item => {
        const date = item.date;
        if (!dailyForecasts[date]) {
            dailyForecasts[date] = [];
        }
        dailyForecasts[date].push(item);
    });
    
    // Create forecast items for unique dates (up to 5 days)
    const forecastDates = Object.keys(dailyForecasts).slice(0, 5);
    
    const forecastItems = forecastDates.map(date => {
        const dayData = dailyForecasts[date];
        // Use the first forecast item for the day (usually around noon)
        const mainForecast = dayData[Math.floor(dayData.length / 2)] || dayData[0];
        const weatherIcon = getWeatherIcon(mainForecast.weather.main);
        
        // Calculate daily min/max from all forecasts for that day
        const temps = dayData.map(f => f.temperature.temp);
        const minTemp = Math.min(...temps);
        const maxTemp = Math.max(...temps);
        
        const dateObj = new Date(date);
        const dayName = dateObj.toLocaleDateString('en-US', { weekday: 'long' });
        const shortDate = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        
        return `
            <div class="forecast-item">
                <div class="forecast-date">
                    <strong>${dayName}</strong><br>
                    ${shortDate}
                </div>
                <div class="forecast-weather">
                    <i class="${weatherIcon}"></i>
                </div>
                <div class="forecast-temp">
                    ${Math.round(maxTemp)}° / ${Math.round(minTemp)}°${unitSymbol}
                </div>
                <div class="forecast-desc">
                    ${mainForecast.weather.description}
                </div>
                <div class="forecast-details">
                    <small>
                        <i class="fas fa-tint"></i> ${mainForecast.humidity}% |
                        <i class="fas fa-wind"></i> ${mainForecast.wind.speed} ${getSpeedUnit(forecastData.units)}
                    </small>
                </div>
            </div>
        `;
    }).join('');
    
    const forecastContainer = `
        <div class="forecast-container">
            <div class="forecast-header">
                <h2>5-Day Forecast for ${forecastData.city}, ${forecastData.country}</h2>
                <p><i class="fas fa-map-marker-alt"></i> ${forecastData.coordinates.lat.toFixed(4)}, ${forecastData.coordinates.lon.toFixed(4)}</p>
            </div>
            <div class="forecast-items">
                ${forecastItems}
            </div>
        </div>
    `;
    
    elements.forecastDisplay.innerHTML = forecastContainer;
}

// Utility Functions
function getUnitSymbol(units) {
    switch (units) {
        case 'imperial': return 'F';
        case 'kelvin': return 'K';
        default: return 'C';
    }
}

function getSpeedUnit(units) {
    switch (units) {
        case 'imperial': return 'mph';
        default: return 'm/s';
    }
}

function getWeatherIcon(weatherMain) {
    const iconMap = {
        'Clear': 'fas fa-sun',
        'Clouds': 'fas fa-cloud',
        'Rain': 'fas fa-cloud-rain',
        'Drizzle': 'fas fa-cloud-drizzle',
        'Thunderstorm': 'fas fa-bolt',
        'Snow': 'fas fa-snowflake',
        'Mist': 'fas fa-smog',
        'Smoke': 'fas fa-smog',
        'Haze': 'fas fa-smog',
        'Dust': 'fas fa-smog',
        'Fog': 'fas fa-smog',
        'Sand': 'fas fa-smog',
        'Ash': 'fas fa-smog',
        'Squall': 'fas fa-wind',
        'Tornado': 'fas fa-tornado'
    };
    
    return iconMap[weatherMain] || 'fas fa-question-circle';
}

// UI State Management
function showLoading() {
    elements.loading.classList.add('show');
}

function hideLoading() {
    elements.loading.classList.remove('show');
}

function showError(message) {
    elements.errorMessage.textContent = message;
    elements.errorDisplay.classList.add('show');
}

function hideError() {
    elements.errorDisplay.classList.remove('show');
}

// Modal Functions
function showApiInfo() {
    elements.apiModal.classList.add('show');
}

function closeApiInfo() {
    elements.apiModal.classList.remove('show');
}

// Close modal when clicking outside
window.addEventListener('click', (e) => {
    if (e.target === elements.apiModal) {
        closeApiInfo();
    }
});

// Keyboard navigation
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeApiInfo();
        hideError();
    }
});

// Auto-focus on city input when current weather tab is active
function focusCurrentWeatherInput() {
    if (document.querySelector('.tab-btn[data-tab="current"]').classList.contains('active')) {
        elements.cityInput.focus();
    }
}

// Initialize focus
setTimeout(focusCurrentWeatherInput, 100);