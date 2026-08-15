const API_BASE = "http://localhost:8000/api";
let allPokemon = [];
let selectedTeam = [];

const searchInput = document.getElementById('pokemon-search');
const suggestionsBox = document.getElementById('suggestions');
const teamSlots = document.querySelectorAll('.slot');
const predictBtn = document.getElementById('predict-btn');
const resultsSection = document.getElementById('results');
const analysisOverlay = document.getElementById('analysis-overlay');
const analysisPhaseText = document.getElementById('analysis-phase');
const analysisStepsList = document.getElementById('analysis-steps');

// Initialize
async function init() {
    try {
        const response = await fetch(`${API_BASE}/pokemon`);
        const data = await response.json();
        allPokemon = data.pokemon;
    } catch (err) {
        console.error("Failed to fetch pokemon list:", err);
    }
}

// Search & Suggestions
searchInput.addEventListener('input', (e) => {
    const val = e.target.value.toLowerCase();
    suggestionsBox.innerHTML = '';
    
    if (val.length < 2) return;

    const matches = allPokemon
        .filter(p => p.includes(val))
        .slice(0, 8);

    matches.forEach(name => {
        const div = document.createElement('div');
        div.className = 'suggestion-item custom-font';
        div.textContent = name.replace(/-/g, ' ');
        div.onclick = () => addPokemon(name);
        suggestionsBox.appendChild(div);
    });
});

document.addEventListener('click', (e) => {
    if (e.target !== searchInput) {
        suggestionsBox.innerHTML = '';
    }
});

function addPokemon(name) {
    if (selectedTeam.length >= 6) return;
    if (selectedTeam.includes(name)) return;

    selectedTeam.push(name);
    searchInput.value = '';
    suggestionsBox.innerHTML = '';
    updateTeamUI();
}

// Exposed to global for onclick in HTML
window.removePokemon = function(index) {
    selectedTeam.splice(index, 1);
    updateTeamUI();
};

async function updateTeamUI() {
    teamSlots.forEach((slot, i) => {
        slot.innerHTML = '';
        slot.className = 'slot';
        
        if (selectedTeam[i]) {
            slot.classList.add('filled');
            const name = selectedTeam[i];
            
            slot.innerHTML = `
                <div class="name custom-font">${name.replace(/-/g, ' ')}</div>
                <div class="loading-spinner">...</div>
                <button class="remove-btn" onclick="removePokemon(${i})">×</button>
            `;
            
            fetchPokemonImage(name, slot);
        } else {
            slot.classList.remove('filled');
            slot.innerHTML = '<span>+</span>';
            slot.onclick = () => searchInput.focus();
        }
    });

    predictBtn.disabled = selectedTeam.length !== 6;
}

async function fetchPokemonImage(name, slot) {
    try {
        const res = await fetch(`https://pokeapi.co/api/v2/pokemon/${name}`);
        const data = await res.json();
        const imgUrl = data.sprites.other['official-artwork'].front_default;
        
        if (slot.classList.contains('filled')) {
            slot.querySelector('.loading-spinner')?.remove();
            
            const img = document.createElement('img');
            img.src = imgUrl;
            slot.appendChild(img);

            if (data.types.length > 0) {
                slot.classList.add(`type-${data.types[0].type.name}`);
            }

            const typesDiv = document.createElement('div');
            typesDiv.className = 'types';
            data.types.forEach(t => {
                const typeName = t.type.name;
                const typeIcon = document.createElement('img');
                typeIcon.src = `assets/symbols/type-${typeName}-badge.png`;
                typeIcon.className = 'type-icon';
                typeIcon.title = typeName;
                typesDiv.appendChild(typeIcon);
            });
            slot.appendChild(typesDiv);
        }
    } catch (err) {
        if (slot.querySelector('.loading-spinner')) {
            slot.querySelector('.loading-spinner').textContent = '?';
        }
    }
}

// Analysis Experience
function addLog(text) {
    const li = document.createElement('li');
    li.className = 'analysis-step-item';
    li.innerHTML = `✓ ${text}`;
    analysisStepsList.appendChild(li);
    li.scrollIntoView({ behavior: 'smooth' });
}

async function runAnalysis() {
    analysisOverlay.classList.remove('hidden');
    analysisStepsList.innerHTML = '';
    
    // Phase 1: Team Scan
    analysisPhaseText.textContent = "Scanning Team Composition...";
    for (let i = 0; i < selectedTeam.length; i++) {
        teamSlots[i].classList.add('highlight');
        addLog(selectedTeam[i].replace(/-/g, ' '));
        await new Promise(resolve => setTimeout(resolve, 200));
        teamSlots[i].classList.remove('highlight');
    }

    // Phase 2: Synergy
    analysisPhaseText.textContent = "Analyzing Team Synergy...";
    const synergyChecks = ["Weather Synergy", "Offensive Presence", "Defensive Presence", "Speed Control"];
    for (const check of synergyChecks) {
        await new Promise(r => setTimeout(resolve, 300));
        addLog(check);
    }

    // Phase 3: Calculation
    analysisPhaseText.textContent = "Calculating Archetype Matchups...";
    await new Promise(r => setTimeout(resolve, 500));
}

// Prediction
predictBtn.onclick = async () => {
    predictBtn.disabled = true;
    
    try {
        // Start fetching immediately
        const predictPromise = fetch(`${API_BASE}/predict`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ team: selectedTeam })
        }).then(res => res.json());

        // Run animation sequence
        analysisOverlay.classList.remove('hidden');
        analysisStepsList.innerHTML = '';
        
        // 1. Scan Phase
        analysisPhaseText.textContent = "Scanning Team Composition...";
        for (let i = 0; i < selectedTeam.length; i++) {
            teamSlots[i].classList.add('highlight');
            addLog(selectedTeam[i].replace(/-/g, ' '));
            await new Promise(resolve => setTimeout(resolve, 150));
            teamSlots[i].classList.remove('highlight');
        }

        // 2. Synergy Phase
        analysisPhaseText.textContent = "Analyzing Team Synergy...";
        const synergyChecks = ["Weather Synergy", "Offensive Presence", "Defensive Presence", "Speed Control"];
        for (const check of synergyChecks) {
            await new Promise(resolve => setTimeout(resolve, 200));
            addLog(check);
        }

        // 3. Matchup Phase
        analysisPhaseText.textContent = "Finalizing Prediction...";
        const data = await predictPromise;
        await new Promise(resolve => setTimeout(resolve, 300));
        
        analysisOverlay.style.opacity = '0';
        setTimeout(() => {
            analysisOverlay.classList.add('hidden');
            analysisOverlay.style.opacity = '1';
            if (data.success) {
                displayResults(data);
            } else {
                alert("Error: " + data.error);
            }
        }, 500);

    } catch (err) {
        alert("Server connection failed.");
        analysisOverlay.classList.add('hidden');
    } finally {
        predictBtn.disabled = false;
    }
};

function displayResults(data) {
    resultsSection.classList.remove('hidden');
    resultsSection.scrollIntoView({ behavior: 'smooth' });

    const archName = data.prediction;
    const archDisplayName = archName.replace(/_/g, ' ');
    
    // Title and Icon
    document.getElementById('prediction-icon').src = `assets/archetypes/${archName}.svg`;
    document.getElementById('archetype-name').textContent = archDisplayName;

    // Alignment Meter
    const maxProb = data.probabilities[archName];
    const alignmentScore = Math.round(maxProb * 100);
    const alignmentBar = document.getElementById('alignment-bar');
    const alignmentValue = document.getElementById('alignment-value');
    
    alignmentBar.style.width = '0%';
    alignmentValue.textContent = '0%';
    
    // Color Interpolation Helper
    const getStatColor = (percent) => {
        if (percent < 25) return "#ff0000"; // Red
        if (percent < 50) return "#ff8000"; // Orange
        if (percent < 75) return "#ffcc00"; // Yellow
        if (percent < 90) return "#80ff00"; // Light Green
        return "#00ff00"; // Green
    };

    setTimeout(() => {
        alignmentBar.style.width = `${alignmentScore}%`;
        alignmentBar.style.backgroundColor = getStatColor(alignmentScore);
        
        let count = 0;
        const interval = setInterval(() => {
            if (count >= alignmentScore) {
                alignmentValue.textContent = `${alignmentScore}%`;
                clearInterval(interval);
            } else {
                count++;
                alignmentValue.textContent = `${count}%`;
            }
        }, 20);
    }, 100);

    // Explanations
    const list = document.getElementById('explanation-list');
    list.innerHTML = '';
    data.explanations.forEach(text => {
        const li = document.createElement('li');
        li.textContent = text;
        list.appendChild(li);
    });

    // Probabilities Chart
    const chart = document.getElementById('prob-chart');
    chart.innerHTML = '';
    
    const sortedProbs = Object.entries(data.probabilities)
        .sort(([,a], [,b]) => b - a);

    sortedProbs.forEach(([label, val], index) => {
        const score = Math.round(val * 100);
        const isPredicted = label === archName;
        
        const row = document.createElement('div');
        row.className = `prob-row ${isPredicted ? 'highlighted' : ''}`;
        row.innerHTML = `
            <div class="prob-label-row">
                <img src="assets/archetypes/${label}.svg" class="archetype-small-icon">
                <span class="label">${label.replace(/_/g, ' ')}</span>
            </div>
            <div class="prob-bar-container">
                <div class="prob-bar-bg">
                    <div class="prob-bar-fill" style="width: 0%"></div>
                </div>
                <span class="prob-val">0%</span>
            </div>
        `;
        chart.appendChild(row);

        // Staggered Animation
        setTimeout(() => {
            const fill = row.querySelector('.prob-bar-fill');
            const valLabel = row.querySelector('.prob-val');
            
            fill.style.width = `${score}%`;
            fill.style.backgroundColor = getStatColor(score);
            valLabel.textContent = `${score}%`;
        }, 200 + (index * 150));
    });
}

// Initialize on load
init();
