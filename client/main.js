const API_BASE = "http://localhost:8000/api";
let allPokemon = [];
let selectedTeam = [];

// DOM Elements
const searchInput = document.getElementById('pokemon-search');
const suggestionsBox = document.getElementById('suggestions');
const teamSlots = document.querySelectorAll('.slot');
const teamCounter = document.getElementById('team-counter');
const predictBtn = document.getElementById('predict-btn');
const synergyBtn = document.getElementById('synergy-btn');
const resultsContainer = document.getElementById('results-container');
const tabArchetype = document.getElementById('tab-archetype');
const tabSynergy = document.getElementById('tab-synergy');
const resultsArchetypeView = document.getElementById('results-archetype');
const resultsSynergyView = document.getElementById('results-synergy');

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

// Search & Autocomplete
let selectedIndex = -1;

function updateHighlight(items) {
    items.forEach((item, idx) => {
        if (idx === selectedIndex) {
            item.classList.add('highlighted');
            item.scrollIntoView({ block: 'nearest' });
        } else {
            item.classList.remove('highlighted');
        }
    });
}

searchInput.addEventListener('input', (e) => {
    const val = e.target.value.toLowerCase().trim();
    suggestionsBox.innerHTML = '';
    selectedIndex = -1;
    
    if (val.length < 2) return;

    const matches = allPokemon
        .filter(p => p.includes(val))
        .slice(0, 8);

    matches.forEach((name, index) => {
        const div = document.createElement('div');
        div.className = 'suggestion-item custom-font';
        div.textContent = name.replace(/-/g, ' ');
        div.dataset.name = name;
        div.onclick = () => addPokemon(name);
        div.addEventListener('mouseenter', () => {
            selectedIndex = index;
            const items = suggestionsBox.querySelectorAll('.suggestion-item');
            items.forEach((item, i) => {
                item.classList.toggle('highlighted', i === selectedIndex);
            });
        });
        suggestionsBox.appendChild(div);
    });
});

searchInput.addEventListener('keydown', (e) => {
    const items = suggestionsBox.querySelectorAll('.suggestion-item');
    if (!items.length) return;

    if (e.key === 'ArrowDown') {
        e.preventDefault();
        selectedIndex = (selectedIndex + 1) % items.length;
        updateHighlight(items);
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        selectedIndex = selectedIndex <= 0 ? items.length - 1 : selectedIndex - 1;
        updateHighlight(items);
    } else if (e.key === 'Enter') {
        e.preventDefault();
        const targetIndex = selectedIndex >= 0 ? selectedIndex : 0;
        const targetItem = items[targetIndex];
        if (targetItem && targetItem.dataset.name) {
            addPokemon(targetItem.dataset.name);
        }
    } else if (e.key === 'Escape') {
        suggestionsBox.innerHTML = '';
        selectedIndex = -1;
    }
});

document.addEventListener('click', (e) => {
    if (e.target !== searchInput) {
        suggestionsBox.innerHTML = '';
        selectedIndex = -1;
    }
});

function addPokemon(name) {
    if (selectedTeam.length >= 6) return;
    if (selectedTeam.includes(name)) return;

    selectedTeam.push(name);
    searchInput.value = '';
    suggestionsBox.innerHTML = '';
    selectedIndex = -1;
    updateTeamUI();
}

window.removePokemon = function(index) {
    selectedTeam.splice(index, 1);
    updateTeamUI();
};

async function updateTeamUI() {
    if (teamCounter) {
        teamCounter.textContent = `${selectedTeam.length} / 6 Selected`;
    }

    teamSlots.forEach((slot, i) => {
        slot.innerHTML = '';
        slot.className = 'slot';
        
        if (selectedTeam[i]) {
            slot.classList.add('filled');
            const name = selectedTeam[i];
            
            slot.innerHTML = `
                <div class="name custom-font">${name.replace(/-/g, ' ')}</div>
                <div class="loading-spinner">...</div>
                <button class="remove-btn" onclick="removePokemon(${i})" title="Remove">×</button>
            `;
            
            fetchPokemonImage(name, slot);
        } else {
            slot.classList.remove('filled');
            slot.innerHTML = '<span>+</span>';
            slot.onclick = () => searchInput.focus();
        }
    });

    const isFull = selectedTeam.length === 6;
    if (predictBtn) predictBtn.disabled = !isFull;
    if (synergyBtn) synergyBtn.disabled = !isFull;
}

async function fetchPokemonImage(name, slot) {
    try {
        const res = await fetch(`https://pokeapi.co/api/v2/pokemon/${name}`);
        const data = await res.json();
        const imgUrl = data.sprites?.other?.['official-artwork']?.front_default;
        
        if (slot.classList.contains('filled')) {
            slot.querySelector('.loading-spinner')?.remove();
            
            if (imgUrl) {
                const img = document.createElement('img');
                img.src = imgUrl;
                img.alt = name;
                slot.appendChild(img);
            }

            if (data.types && data.types.length > 0) {
                slot.classList.add(`type-${data.types[0].type.name}`);
            }

            const typesDiv = document.createElement('div');
            typesDiv.className = 'types';
            data.types?.forEach(t => {
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

// Log Helper for Overlay Animation
function addLog(text) {
    const li = document.createElement('li');
    li.className = 'analysis-step-item';
    li.innerHTML = `<span class="retro-bullet">▶</span> ${text}`;
    analysisStepsList.appendChild(li);
    li.scrollIntoView({ behavior: 'smooth' });
}

// Tab Switching
window.switchResultTab = function(tab) {
    if (tab === 'archetype') {
        tabArchetype.classList.add('active');
        tabSynergy.classList.remove('active');
        resultsArchetypeView.classList.remove('hidden');
        resultsSynergyView.classList.add('hidden');
    } else if (tab === 'synergy') {
        tabSynergy.classList.add('active');
        tabArchetype.classList.remove('active');
        resultsSynergyView.classList.remove('hidden');
        resultsArchetypeView.classList.add('hidden');
    }
};

// =============================================================
// 1. RUN ARCHETYPE PREDICTION
// =============================================================
if (predictBtn) {
    predictBtn.onclick = async () => {
        if (selectedTeam.length !== 6) return;
        predictBtn.disabled = true;
        
        try {
            const predictPromise = fetch(`${API_BASE}/predict`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ team: selectedTeam })
            }).then(res => res.json());

            analysisOverlay.classList.remove('hidden');
            analysisStepsList.innerHTML = '';
            
            // Phase 1: Team Scan
            analysisPhaseText.textContent = "Scanning Team Composition...";
            for (let i = 0; i < selectedTeam.length; i++) {
                teamSlots[i].classList.add('highlight');
                addLog(selectedTeam[i].replace(/-/g, ' '));
                await new Promise(resolve => setTimeout(resolve, 150));
                teamSlots[i].classList.remove('highlight');
            }

            // Phase 2: Synergy Scan
            analysisPhaseText.textContent = "Analyzing Strategic Signatures...";
            const synergyChecks = ["Weather Abilities", "Stat Variance", "Speed Distribution", "Offensive Bulk"];
            for (const check of synergyChecks) {
                await new Promise(resolve => setTimeout(resolve, 180));
                addLog(check);
            }

            // Phase 3: Finalizing
            analysisPhaseText.textContent = "Calculating Archetype Probabilities...";
            const data = await predictPromise;
            await new Promise(resolve => setTimeout(resolve, 250));
            
            analysisOverlay.style.opacity = '0';
            setTimeout(() => {
                analysisOverlay.classList.add('hidden');
                analysisOverlay.style.opacity = '1';
                if (data.success) {
                    displayArchetypeResults(data);
                } else {
                    alert("Error: " + data.error);
                }
            }, 400);

        } catch (err) {
            alert("Server connection failed.");
            analysisOverlay.classList.add('hidden');
        } finally {
            predictBtn.disabled = selectedTeam.length !== 6;
        }
    };
}

function displayArchetypeResults(data) {
    resultsContainer.classList.remove('hidden');
    switchResultTab('archetype');
    resultsContainer.scrollIntoView({ behavior: 'smooth' });

    const archName = data.prediction;
    const archDisplayName = archName.replace(/_/g, ' ');
    
    // Title and Icon
    document.getElementById('prediction-icon').src = `assets/archetypes/${archName}.svg`;
    document.getElementById('archetype-name').textContent = archDisplayName;

    // Alignment Meter
    const maxProb = data.probabilities[archName] || 0;
    const alignmentScore = Math.round(maxProb * 100);
    const alignmentBar = document.getElementById('alignment-bar');
    const alignmentValue = document.getElementById('alignment-value');
    
    alignmentBar.style.width = '0%';
    alignmentValue.textContent = '0%';
    
    const getStatColor = (percent) => {
        if (percent < 25) return "#ff3333";
        if (percent < 50) return "#ff9800";
        if (percent < 75) return "#ffcc00";
        if (percent < 90) return "#4caf50";
        return "#2e7d32";
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
        }, 15);
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
                <img src="assets/archetypes/${label}.svg" class="archetype-small-icon" alt="">
                <span class="label custom-font">${label.replace(/_/g, ' ')}</span>
            </div>
            <div class="prob-bar-container">
                <div class="prob-bar-bg">
                    <div class="prob-bar-fill" style="width: 0%"></div>
                </div>
                <span class="prob-val custom-font">0%</span>
            </div>
        `;
        chart.appendChild(row);

        setTimeout(() => {
            const fill = row.querySelector('.prob-bar-fill');
            const valLabel = row.querySelector('.prob-val');
            
            fill.style.width = `${score}%`;
            fill.style.backgroundColor = getStatColor(score);
            valLabel.textContent = `${score}%`;
        }, 150 + (index * 120));
    });
}

// =============================================================
// 2. RUN TEAM SYNERGY ANALYSIS
// =============================================================
if (synergyBtn) {
    synergyBtn.onclick = async () => {
        if (selectedTeam.length !== 6) return;
        synergyBtn.disabled = true;
        
        try {
            const synergyPromise = fetch(`${API_BASE}/synergy`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ team: selectedTeam })
            }).then(res => res.json());

            analysisOverlay.classList.remove('hidden');
            analysisStepsList.innerHTML = '';
            
            // Phase 1: Team Scan
            analysisPhaseText.textContent = "Scanning Team Composition...";
            for (let i = 0; i < selectedTeam.length; i++) {
                teamSlots[i].classList.add('highlight');
                addLog(selectedTeam[i].replace(/-/g, ' '));
                await new Promise(resolve => setTimeout(resolve, 150));
                teamSlots[i].classList.remove('highlight');
            }

            // Phase 2: Defense Scan
            analysisPhaseText.textContent = "Calculating Type Defenses & Multipliers...";
            const checks = ["Dual-Type Defense Matrix", "Shared Weaknesses", "Physical / Special Split", "Speed Tier Balance", "Weather & Strategy Cohesion"];
            for (const check of checks) {
                await new Promise(resolve => setTimeout(resolve, 180));
                addLog(check);
            }

            // Phase 3: Finalizing Report
            analysisPhaseText.textContent = "Compiling Team Synergy Report...";
            const data = await synergyPromise;
            await new Promise(resolve => setTimeout(resolve, 250));
            
            analysisOverlay.style.opacity = '0';
            setTimeout(() => {
                analysisOverlay.classList.add('hidden');
                analysisOverlay.style.opacity = '1';
                if (data.success) {
                    displaySynergyResults(data);
                } else {
                    alert("Error: " + data.error);
                }
            }, 400);

        } catch (err) {
            alert("Server connection failed.");
            analysisOverlay.classList.add('hidden');
        } finally {
            synergyBtn.disabled = selectedTeam.length !== 6;
        }
    };
}

function displaySynergyResults(data) {
    resultsContainer.classList.remove('hidden');
    switchResultTab('synergy');
    resultsContainer.scrollIntoView({ behavior: 'smooth' });

    const overall = data.overall;
    
    // Overall Score Dial & Rating Badge
    const scoreVal = document.getElementById('synergy-score-val');
    const ratingBadge = document.getElementById('synergy-rating-badge');
    const summaryTitle = document.getElementById('synergy-summary-title');
    const summaryDesc = document.getElementById('synergy-summary-desc');

    scoreVal.textContent = overall.score;
    ratingBadge.textContent = overall.rating.toUpperCase();
    ratingBadge.className = `badge custom-font badge-${overall.rating_color}`;
    summaryTitle.textContent = `${overall.rating} Strategic Synergy`;
    summaryDesc.textContent = overall.summary;

    // Sub-Scores
    const updateSubScore = (valId, barId, score) => {
        const valElem = document.getElementById(valId);
        const barElem = document.getElementById(barId);
        if (valElem && barElem) {
            valElem.textContent = `${score}%`;
            barElem.style.width = '0%';
            setTimeout(() => {
                barElem.style.width = `${score}%`;
            }, 150);
        }
    };

    updateSubScore('subscore-def-val', 'subscore-def-bar', overall.defensive_score);
    updateSubScore('subscore-off-val', 'subscore-off-bar', overall.offensive_score);
    updateSubScore('subscore-strat-val', 'subscore-strat-bar', overall.strategic_score);

    // Strengths Cards
    const strengthsContainer = document.getElementById('synergy-strengths-list');
    strengthsContainer.innerHTML = '';
    data.strengths.forEach(s => {
        const card = document.createElement('div');
        card.className = 'synergy-item-card card-strength';
        card.innerHTML = `
            <div class="item-card-top">
                <h4 class="custom-font item-title">${s.title}</h4>
                <span class="badge badge-tag custom-font">${s.tag}</span>
            </div>
            <p class="item-desc">${s.description}</p>
        `;
        strengthsContainer.appendChild(card);
    });

    // Gaps Cards
    const gapsContainer = document.getElementById('synergy-gaps-list');
    gapsContainer.innerHTML = '';
    data.gaps.forEach(g => {
        const card = document.createElement('div');
        card.className = `synergy-item-card card-gap gap-${g.severity || 'warning'}`;
        card.innerHTML = `
            <div class="item-card-top">
                <h4 class="custom-font item-title">${g.title}</h4>
                <span class="badge badge-tag-gap custom-font">${g.tag}</span>
            </div>
            <p class="item-desc">${g.description}</p>
        `;
        gapsContainer.appendChild(card);
    });

    // Type Matchup Matrix Grid
    const matrixGrid = document.getElementById('type-matchup-grid');
    matrixGrid.innerHTML = '';
    
    if (data.type_matchups) {
        Object.entries(data.type_matchups).forEach(([typeName, m]) => {
            const pill = document.createElement('div');
            pill.className = `type-matrix-pill pill-${m.status}`;
            
            let statusText = "Balanced";
            if (m.status === 'danger') statusText = `${m.weak_count} Weak / ${m.resist_count + m.immune_count} Res`;
            else if (m.status === 'warning') statusText = `${m.weak_count} Weak / 0 Res`;
            else if (m.status === 'strength') statusText = `${m.resist_count + m.immune_count} Resists`;

            pill.innerHTML = `
                <div class="pill-type-header">
                    <img src="assets/symbols/type-${typeName}-badge.png" class="pill-type-icon" alt="${typeName}">
                    <span class="pill-type-name custom-font">${typeName.toUpperCase()}</span>
                </div>
                <div class="pill-status-tag custom-font">${statusText}</div>
            `;
            
            if (m.weak_pokemon && m.weak_pokemon.length > 0) {
                pill.title = `Weak: ${m.weak_pokemon.join(', ')}`;
            }
            matrixGrid.appendChild(pill);
        });
    }

    // Offensive Profile
    const off = data.offensive_profile;
    if (off) {
        document.getElementById('split-phys-count').textContent = off.physical_attackers;
        document.getElementById('split-spec-count').textContent = off.special_attackers;
        document.getElementById('split-mix-count').textContent = off.mixed_attackers;

        document.getElementById('speed-fast-count').textContent = off.fast_count;
        document.getElementById('speed-mid-count').textContent = off.mid_count;
        document.getElementById('speed-slow-count').textContent = off.slow_count;

        document.getElementById('coverage-count-val').textContent = off.coverage_count;
    }

    // Beginner Guide
    if (data.beginner_guide) {
        document.getElementById('beginner-summary-text').textContent = data.beginner_guide.summary;
    }
}

// Start
init();
