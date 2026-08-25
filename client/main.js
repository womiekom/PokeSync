const API_BASE = "http://localhost:8000/api";
let allPokemon = [];
let selectedTeam = [];
let currentFormat = "gen9ou";
let predictedArchetype = "balance";

// Cached Moveset Results for all 6 members
let teamMovesetCache = {};
let activeMovesetIndex = 0;

// DOM Elements
const searchInput = document.getElementById('pokemon-search');
const suggestionsBox = document.getElementById('suggestions');
const teamSlots = document.querySelectorAll('.slot');
const teamCounter = document.getElementById('team-counter');
const predictBtn = document.getElementById('predict-btn');
const synergyBtn = document.getElementById('synergy-btn');
const movesetBtn = document.getElementById('moveset-btn');
const optimizerBtn = document.getElementById('optimizer-btn');
const resultsContainer = document.getElementById('results-container');

// Tabs
const tabArchetype = document.getElementById('tab-archetype');
const tabSynergy = document.getElementById('tab-synergy');
const tabMoveset = document.getElementById('tab-moveset');
const tabOptimizer = document.getElementById('tab-optimizer');

// Views
const resultsArchetypeView = document.getElementById('results-archetype');
const resultsSynergyView = document.getElementById('results-synergy');
const resultsMovesetView = document.getElementById('results-moveset');
const resultsOptimizerView = document.getElementById('results-optimizer');

// Overlay
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

// Format Selector Toggle
window.setFormat = function(fmt) {
    currentFormat = fmt;
    const ouBtn = document.getElementById('format-btn-ou');
    const vgcBtn = document.getElementById('format-btn-vgc');
    if (ouBtn) ouBtn.classList.toggle('active', fmt === 'gen9ou');
    if (vgcBtn) vgcBtn.classList.toggle('active', fmt === 'gen9vgc');
    
    const badge = document.getElementById('moveset-format-badge');
    if (badge) {
        badge.textContent = fmt === 'gen9ou' ? 'GEN 9 OU' : 'GEN 9 VGC';
    }
};

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
    if (movesetBtn) movesetBtn.disabled = !isFull;
    if (optimizerBtn) optimizerBtn.disabled = !isFull;
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
    [tabArchetype, tabSynergy, tabMoveset, tabOptimizer].forEach(t => t?.classList.remove('active'));
    [resultsArchetypeView, resultsSynergyView, resultsMovesetView, resultsOptimizerView].forEach(v => v?.classList.add('hidden'));

    if (tab === 'archetype') {
        tabArchetype?.classList.add('active');
        resultsArchetypeView?.classList.remove('hidden');
    } else if (tab === 'synergy') {
        tabSynergy?.classList.add('active');
        resultsSynergyView?.classList.remove('hidden');
    } else if (tab === 'moveset') {
        tabMoveset?.classList.add('active');
        resultsMovesetView?.classList.remove('hidden');
    } else if (tab === 'optimizer') {
        tabOptimizer?.classList.add('active');
        resultsOptimizerView?.classList.remove('hidden');
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
            
            analysisPhaseText.textContent = "Scanning Team Composition...";
            for (let i = 0; i < selectedTeam.length; i++) {
                teamSlots[i].classList.add('highlight');
                addLog(selectedTeam[i].replace(/-/g, ' '));
                await new Promise(resolve => setTimeout(resolve, 120));
                teamSlots[i].classList.remove('highlight');
            }

            analysisPhaseText.textContent = "Analyzing Strategic Signatures...";
            const synergyChecks = ["Weather Abilities", "Stat Variance", "Speed Distribution", "Offensive Bulk"];
            for (const check of synergyChecks) {
                await new Promise(resolve => setTimeout(resolve, 140));
                addLog(check);
            }

            analysisPhaseText.textContent = "Calculating Archetype Probabilities...";
            const data = await predictPromise;
            await new Promise(resolve => setTimeout(resolve, 200));
            
            analysisOverlay.style.opacity = '0';
            setTimeout(() => {
                analysisOverlay.classList.add('hidden');
                analysisOverlay.style.opacity = '1';
                if (data.success) {
                    predictedArchetype = data.prediction;
                    displayArchetypeResults(data);
                } else {
                    alert("Error: " + data.error);
                }
            }, 300);

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
    
    document.getElementById('prediction-icon').src = `assets/archetypes/${archName}.svg`;
    document.getElementById('archetype-name').textContent = archDisplayName;

    const maxProb = data.probabilities[archName] || 0;
    const alignmentScore = Math.round(maxProb * 100);
    const alignmentBar = document.getElementById('alignment-bar');
    const alignmentValue = document.getElementById('alignment-value');
    
    alignmentBar.style.width = '0%';
    alignmentValue.textContent = '0%';
    
    const getStatColor = (percent) => {
        if (percent < 25) return "#ff3333";
        if (percent < 50) return "#ff9800";
        if (percent < 75) return "#2196f3";
        return "#4caf50";
    };

    setTimeout(() => {
        alignmentBar.style.width = `${alignmentScore}%`;
        alignmentBar.style.backgroundColor = getStatColor(alignmentScore);
        alignmentValue.textContent = `${alignmentScore}%`;
    }, 100);

    const expList = document.getElementById('explanation-list');
    expList.innerHTML = '';
    data.explanations.forEach((text, i) => {
        const li = document.createElement('li');
        li.style.animationDelay = `${i * 0.1}s`;
        li.innerHTML = `<span class="bullet-icon">✦</span> ${text}`;
        expList.appendChild(li);
    });

    const probChart = document.getElementById('prob-chart');
    probChart.innerHTML = '';
    Object.entries(data.probabilities)
        .sort((a, b) => b[1] - a[1])
        .forEach(([arch, prob], i) => {
            const row = document.createElement('div');
            row.className = 'prob-row';
            const percent = Math.round(prob * 100);
            
            row.innerHTML = `
                <div class="prob-info">
                    <span class="prob-name custom-font">${arch.replace(/_/g, ' ')}</span>
                    <span class="prob-val custom-font">${percent}%</span>
                </div>
                <div class="prob-bar-bg">
                    <div class="prob-bar-fill" style="width: 0%; background-color: ${getStatColor(percent)};"></div>
                </div>
            `;
            probChart.appendChild(row);

            setTimeout(() => {
                row.querySelector('.prob-bar-fill').style.width = `${percent}%`;
            }, 100 + (i * 60));
        });
}

// =============================================================
// 2. RUN TEAM SYNERGY ENGINE
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
            
            analysisPhaseText.textContent = "Calculating Elemental Defenses...";
            const defChecks = ["Evaluating 18 Type Multipliers", "Checking 4x Weaknesses", "Tallying Immunities"];
            for (const check of defChecks) {
                await new Promise(resolve => setTimeout(resolve, 140));
                addLog(check);
            }

            analysisPhaseText.textContent = "Assessing Offensive Coverage...";
            const offChecks = ["Measuring STAB Type Spread", "Auditing Speed Tiers", "Analyzing Damage Distribution"];
            for (const check of offChecks) {
                await new Promise(resolve => setTimeout(resolve, 140));
                addLog(check);
            }

            const data = await synergyPromise;
            
            analysisOverlay.style.opacity = '0';
            setTimeout(() => {
                analysisOverlay.classList.add('hidden');
                analysisOverlay.style.opacity = '1';
                if (data.success) {
                    displaySynergyResults(data);
                } else {
                    alert("Error: " + data.error);
                }
            }, 300);

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
    const scoreVal = document.getElementById('synergy-score-val');
    const scoreRing = document.getElementById('synergy-score-ring');
    const ratingBadge = document.getElementById('synergy-rating-badge');
    const summaryTitle = document.getElementById('synergy-summary-title');
    const summaryDesc = document.getElementById('synergy-summary-desc');

    if (scoreVal) scoreVal.textContent = overall.score;
    if (scoreRing) {
        scoreRing.style.setProperty('--score-angle', `${(overall.score / 100) * 360}deg`);
        scoreRing.style.background = `conic-gradient(${overall.rating_color} ${(overall.score / 100) * 360}deg, #e0e0e0 0deg)`;
    }
    if (ratingBadge) {
        ratingBadge.textContent = overall.rating;
        ratingBadge.style.backgroundColor = overall.rating_color;
    }
    if (summaryTitle) summaryTitle.textContent = `${overall.rating} Team Balance`;
    if (summaryDesc) summaryDesc.textContent = overall.summary;

    const setSubscore = (id, val, barId) => {
        const el = document.getElementById(id);
        const bar = document.getElementById(barId);
        if (el) el.textContent = `${val}%`;
        if (bar) {
            bar.style.width = `${val}%`;
            bar.style.backgroundColor = val >= 70 ? '#4caf50' : (val >= 50 ? '#ff9800' : '#f44336');
        }
    };

    setSubscore('subscore-def-val', overall.defensive_score, 'subscore-def-bar');
    setSubscore('subscore-off-val', overall.offensive_score, 'subscore-off-bar');
    setSubscore('subscore-strat-val', overall.strategic_score, 'subscore-strat-bar');

    const strengthsList = document.getElementById('synergy-strengths-list');
    if (strengthsList) {
        strengthsList.innerHTML = '';
        data.strengths.forEach(s => {
            const card = document.createElement('div');
            card.className = 'synergy-point-card card-strength';
            card.innerHTML = `
                <div class="point-header">
                    <span class="point-title custom-font">${s.title}</span>
                    <span class="point-tag custom-font">${s.tag.toUpperCase()}</span>
                </div>
                <p class="point-desc">${s.description}</p>
            `;
            strengthsList.appendChild(card);
        });
    }

    const gapsList = document.getElementById('synergy-gaps-list');
    if (gapsList) {
        gapsList.innerHTML = '';
        data.gaps.forEach(g => {
            const card = document.createElement('div');
            card.className = `synergy-point-card card-gap severity-${g.severity}`;
            card.innerHTML = `
                <div class="point-header">
                    <span class="point-title custom-font">${g.title}</span>
                    <span class="point-tag custom-font">${g.severity.toUpperCase()}</span>
                </div>
                <p class="point-desc">${g.description}</p>
            `;
            gapsList.appendChild(card);
        });
    }

    const matrixGrid = document.getElementById('type-matchup-grid');
    if (matrixGrid && data.type_matchups) {
        matrixGrid.innerHTML = '';
        Object.entries(data.type_matchups).forEach(([typeName, matchup]) => {
            const item = document.createElement('div');
            item.className = `matrix-cell status-${matchup.status}`;
            item.innerHTML = `
                <div class="cell-top">
                    <img src="assets/symbols/type-${typeName}-badge.png" class="matrix-type-icon" title="${typeName}">
                    <span class="cell-name custom-font">${typeName.slice(0, 3).toUpperCase()}</span>
                </div>
                <div class="cell-stats">
                    <span class="stat-weak" title="Weaknesses">▲${matchup.weak_count}</span>
                    <span class="stat-res" title="Resistances/Immunities">▼${matchup.resist_count + matchup.immune_count}</span>
                </div>
            `;
            matrixGrid.appendChild(item);
        });
    }

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
}

// =============================================================
// 3. RUN MOVESET RECOMMENDER (PHASE 3)
// =============================================================
if (movesetBtn) {
    movesetBtn.onclick = async () => {
        if (selectedTeam.length !== 6) return;
        movesetBtn.disabled = true;

        try {
            analysisOverlay.classList.remove('hidden');
            analysisStepsList.innerHTML = '';
            analysisPhaseText.textContent = "Extracting Legal Movepools...";
            addLog("Querying Showdown Legal Learnsets");
            addLog("Analyzing Teammate Type Coverage Gaps");
            addLog("Ranking via Smogon High-Ladder Telemetry");

            // Fetch recommendations for all 6 team members concurrently
            const promises = selectedTeam.map(name => 
                fetch(`${API_BASE}/recommend/moveset`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        pokemon: name,
                        team: selectedTeam.filter(n => n !== name),
                        archetype: predictedArchetype,
                        format: currentFormat
                    })
                }).then(res => res.json())
            );

            const results = await Promise.all(promises);
            teamMovesetCache = {};
            selectedTeam.forEach((name, idx) => {
                if (results[idx].success) {
                    teamMovesetCache[name] = results[idx];
                }
            });

            analysisOverlay.style.opacity = '0';
            setTimeout(() => {
                analysisOverlay.classList.add('hidden');
                analysisOverlay.style.opacity = '1';
                displayMovesetResults();
            }, 300);

        } catch (err) {
            alert("Moveset recommendation failed.");
            analysisOverlay.classList.add('hidden');
        } finally {
            movesetBtn.disabled = selectedTeam.length !== 6;
        }
    };
}

function displayMovesetResults() {
    resultsContainer.classList.remove('hidden');
    switchResultTab('moveset');
    resultsContainer.scrollIntoView({ behavior: 'smooth' });

    const pillsContainer = document.getElementById('moveset-member-pills');
    pillsContainer.innerHTML = '';

    selectedTeam.forEach((name, idx) => {
        const pill = document.createElement('button');
        pill.className = `member-pill custom-font ${idx === activeMovesetIndex ? 'active' : ''}`;
        pill.innerHTML = `<span>${name.replace(/-/g, ' ')}</span>`;
        pill.onclick = () => {
            activeMovesetIndex = idx;
            document.querySelectorAll('.member-pill').forEach((p, i) => {
                p.classList.toggle('active', i === idx);
            });
            renderActivePokemonMoveset(name);
        };
        pillsContainer.appendChild(pill);
    });

    const activeMon = selectedTeam[activeMovesetIndex] || selectedTeam[0];
    renderActivePokemonMoveset(activeMon);
}

function renderActivePokemonMoveset(pokemonName) {
    const data = teamMovesetCache[pokemonName];
    if (!data) return;

    document.getElementById('moveset-pokemon-title').textContent = `${data.pokemon} Moveset Plan`;
    document.getElementById('moveset-summary-desc').textContent = data.archetype_fit_summary || "Context-aware competitive moveset recommendation.";

    const grid = document.getElementById('moveset-grid');
    grid.innerHTML = '';

    data.recommended_moves.forEach((move, i) => {
        const card = document.createElement('div');
        card.className = `move-card move-cat-${move.category.toLowerCase()}`;
        card.innerHTML = `
            <div class="move-card-header">
                <div class="move-title-wrap">
                    <img src="assets/symbols/type-${move.type.toLowerCase()}-badge.png" class="move-type-icon" title="${move.type}">
                    <span class="move-name custom-font">${move.name}</span>
                </div>
                <span class="move-role-badge custom-font">${move.role_tag}</span>
            </div>
            <div class="move-stats-row">
                <span class="move-stat-item custom-font">PWR: <strong>${move.power > 0 ? move.power : '--'}</strong></span>
                <span class="move-stat-item custom-font">ACC: <strong>${move.accuracy}%</strong></span>
                <span class="move-stat-item custom-font">CAT: <strong>${move.category}</strong></span>
                <span class="move-stat-item custom-font">SCORE: <strong>${move.score}</strong></span>
            </div>
            <p class="move-rationale">${move.rationale}</p>
        `;
        grid.appendChild(card);
    });

    // Tera Types
    const teraList = document.getElementById('moveset-tera-list');
    teraList.innerHTML = '';
    (data.recommended_tera_types || []).forEach(t => {
        const badge = document.createElement('div');
        badge.className = 'tera-badge custom-font';
        badge.innerHTML = `
            <img src="assets/symbols/type-${t.toLowerCase()}-badge.png" class="mini-type-icon">
            <span>Tera ${t}</span>
        `;
        teraList.appendChild(badge);
    });

    // Items
    const itemList = document.getElementById('moveset-item-list');
    itemList.innerHTML = '';
    (data.recommended_items || []).forEach(it => {
        const itemTag = document.createElement('div');
        itemTag.className = 'item-badge custom-font';
        itemTag.innerHTML = `<span>❖ ${it}</span>`;
        itemList.appendChild(itemTag);
    });
}

// =============================================================
// 4. RUN TEAM OPTIMIZER (PHASE 3)
// =============================================================
if (optimizerBtn) {
    optimizerBtn.onclick = async () => {
        if (selectedTeam.length !== 6) return;
        optimizerBtn.disabled = true;

        try {
            analysisOverlay.classList.remove('hidden');
            analysisStepsList.innerHTML = '';
            analysisPhaseText.textContent = "Simulating Replacements...";
            addLog("Evaluating Baseline Synergy Score");
            addLog("Auditing Critical Defensive Vulnerabilities");
            addLog("Simulating Top High-Ladder Candidate Swaps");

            const response = await fetch(`${API_BASE}/optimize/team`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    team: selectedTeam,
                    format: currentFormat,
                    target_archetype: predictedArchetype
                })
            });

            const data = await response.json();

            analysisOverlay.style.opacity = '0';
            setTimeout(() => {
                analysisOverlay.classList.add('hidden');
                analysisOverlay.style.opacity = '1';
                if (data.success) {
                    displayOptimizerResults(data);
                } else {
                    alert("Error: " + data.error);
                }
            }, 300);

        } catch (err) {
            alert("Team optimization failed.");
            analysisOverlay.classList.add('hidden');
        } finally {
            optimizerBtn.disabled = selectedTeam.length !== 6;
        }
    };
}

function displayOptimizerResults(data) {
    resultsContainer.classList.remove('hidden');
    switchResultTab('optimizer');
    resultsContainer.scrollIntoView({ behavior: 'smooth' });

    document.getElementById('opt-current-score').textContent = `${data.baseline_score} / 100`;

    // Gaps box
    const gapsBox = document.getElementById('optimizer-gaps-box');
    gapsBox.innerHTML = '';
    if (data.gaps_detected && data.gaps_detected.length > 0) {
        data.gaps_detected.forEach(g => {
            const alertItem = document.createElement('div');
            alertItem.className = `gap-alert-item severity-${g.severity}`;
            alertItem.innerHTML = `
                <div class="gap-alert-title custom-font">⚠ ${g.title}</div>
                <div class="gap-alert-desc">${g.description}</div>
            `;
            gapsBox.appendChild(alertItem);
        });
    }

    // Suggestions Stack
    const suggestionsList = document.getElementById('optimizer-suggestions-list');
    suggestionsList.innerHTML = '';

    if (!data.suggestions || data.suggestions.length === 0) {
        suggestionsList.innerHTML = `<div class="no-opt-msg custom-font">Your team already exhibits peak synergy! No high-value replacements needed.</div>`;
        return;
    }

    data.suggestions.forEach((sug, i) => {
        const card = document.createElement('div');
        card.className = 'optimizer-proposal-card card-inner';
        
        let improvedMatchupBadges = sug.improved_matchups.map(t => 
            `<span class="matchup-pill-green custom-font">+ ${t}</span>`
        ).join(' ');

        card.innerHTML = `
            <div class="proposal-top">
                <div class="swap-species-row">
                    <div class="swap-mon remove-mon custom-font">
                        <span class="swap-action-tag remove-tag">REMOVE</span>
                        <span class="swap-name">${sug.remove_pokemon}</span>
                    </div>
                    <div class="swap-arrow custom-font">➔</div>
                    <div class="swap-mon add-mon custom-font">
                        <span class="swap-action-tag add-tag">ADD</span>
                        <span class="swap-name">${sug.add_pokemon}</span>
                    </div>
                </div>
                <div class="score-delta-badge custom-font">
                    +${sug.score_delta} Score
                </div>
            </div>
            <p class="proposal-rationale">${sug.rationale}</p>
            <div class="proposal-bottom-row">
                <div class="improved-tags-container">
                    ${improvedMatchupBadges ? `<span class="improved-lbl custom-font">PATCHES:</span> ${improvedMatchupBadges}` : ''}
                </div>
                <button class="custom-font swap-btn" onclick="applySwap('${sug.remove_pokemon_raw}', '${sug.add_pokemon_raw}')">
                    <span>SWAP INTO TEAM</span>
                </button>
            </div>
        `;
        suggestionsList.appendChild(card);
    });
}

window.applySwap = function(oldName, newName) {
    const idx = selectedTeam.indexOf(oldName);
    if (idx !== -1) {
        selectedTeam[idx] = newName;
        updateTeamUI();
        // Trigger optimizer refresh
        if (optimizerBtn) optimizerBtn.click();
    }
};

// Start
init();
