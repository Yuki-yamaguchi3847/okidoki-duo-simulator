document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const creditsEl = document.getElementById('credits');
    const modeEl = document.getElementById('current-mode');
    const gamesSinceBonusEl = document.getElementById('games-since-bonus');
    const totalGamesEl = document.getElementById('total-games');
    const spinButton = document.getElementById('spin-button');
    const skipButton = document.getElementById('skip-button');
    const skipATButton = document.getElementById('skip-at-button');
    const hibiscusImg = document.getElementById('hibiscus-img');
    const messageLog = document.getElementById('last-action-message');
    const bonusHistoryLogEl = document.getElementById('bonus-history-log');
    const chartCanvas = document.getElementById('credit-chart');
    const renchanCountEl = document.getElementById('renchan-count');
    const renchanPayoutEl = document.getElementById('renchan-payout');
    const oneGRenOverlay = document.getElementById('one-g-ren-overlay');

    // --- Game and History Initialization ---
    let player = { credits: 3000 };
    let gameState = new GameState(typeof SETTING_LEVEL !== 'undefined' ? SETTING_LEVEL : 1, true);
    let creditHistory = [{x: 0, y: 3000}];
    let creditChart;
    let gamesFromPreviousBonusForLog = 0;

    // --- Chart.js Initialization ---
    function initializeChart() {
        Chart.defaults.color = '#aaa';
        const ctx = chartCanvas.getContext('2d');
        creditChart = new Chart(ctx, {
            type: 'line',
            data: { datasets: [{ data: creditHistory, borderColor: '#ffc107', borderWidth: 2, tension: 0.1, pointRadius: 0 }] },
            options: {
                animation: false,
                scales: {
                    x: { type: 'linear', title: { display: true, text: 'Total Games' }, grid: { color: 'rgba(255, 255, 255, 0.1)' } },
                    y: { title: { display: true, text: 'Credits' }, grid: { color: 'rgba(255, 255, 255, 0.1)' } }
                },
                plugins: { legend: { display: false } }
            }
        });
    }

    function updateChart() {
        // Optimization: only sample data for performance
        const maxPoints = 5000;
        const step = Math.max(1, Math.floor(creditHistory.length / maxPoints));
        const sampledData = creditHistory.filter((_, i) => i % step === 0);
        if (sampledData[sampledData.length - 1] !== creditHistory[creditHistory.length - 1]) {
            sampledData.push(creditHistory[creditHistory.length - 1]);
        }
        creditChart.data.datasets[0].data = sampledData;
        creditChart.update('none');
    }

    function addBonusToLog(type) {
        const li = document.createElement('li');
        const bonusClass = type === 'BIG' ? 'bonus-big' : 'bonus-reg';
        li.innerHTML = `<span class="${bonusClass}">${type}</span> at game ${gameState.total_games} (${gamesFromPreviousBonusForLog}G)`;
        bonusHistoryLogEl.prepend(li);
    }
    
    function updateUI() {
        creditsEl.textContent = player.credits;
        if (gameState.is_in_bonus_at) {
            const total = BONUS_GAMES[gameState.current_bonus_type];
            const remaining = gameState.bonus_games_remaining;
            modeEl.textContent = `${gameState.current_bonus_type} AT (${total - remaining}/${total}G)`;
            skipATButton.style.display = 'inline-block';
            skipButton.style.display = 'none';
        } else {
            modeEl.textContent = gameState.current_mode;
            skipATButton.style.display = 'none';
            skipButton.style.display = 'inline-block';
        }
        gamesSinceBonusEl.textContent = gameState.games_since_bonus;
        totalGamesEl.textContent = gameState.total_games;
        renchanCountEl.textContent = gameState.renchan_count;
        renchanPayoutEl.textContent = gameState.renchan_payout;
    }

    function showMessage(msg, isBonus = false) {
        messageLog.textContent = msg;
        messageLog.style.color = isBonus ? "#ff4848" : "#ffc107";
    }

    function setButtonsDisabled(disabled) {
        spinButton.disabled = disabled;
        skipButton.disabled = disabled;
        skipATButton.disabled = disabled;
    }

    function processEvents(events) {
        let bonusHitInSpin = false;
        let bonusEndInSpin = false;

        events.forEach(event => {
            switch(event.event) {
                case 'BONUS_START':
                    hibiscusImg.src = "images/hibiscus_on.svg";
                    hibiscusImg.classList.add('lit');
                    gamesFromPreviousBonusForLog = event.games_since_bonus;
                    addBonusToLog(event.type);
                    showMessage(`🎉 ${event.type} BONUS START! 🎉`, true);
                    bonusHitInSpin = true;
                    break;
                case 'BONUS_END':
                    bonusEndInSpin = true;
                    if (event.renchan_streak_ended) {
                        showMessage(`天国終了: ${event.renchan_count}連荘 / ${event.renchan_payout}枚`);
                    } else {
                        showMessage(`Bonus End. Next mode: ${event.mode_changed_to}`);
                    }
                    break;
                case 'RENCHAN_STREAK_END':
                    showMessage(`天国終了: ${event.renchan_count}連荘 / ${event.renchan_payout}枚`);
                    break;
                case '1G_REN':
                    hibiscusImg.src = "images/hibiscus_on.svg";
                    hibiscusImg.classList.add('lit');
                    addBonusToLog(event.type);
                    showMessage(`⚡️ 1G-REN! ${event.type} BONUS! ⚡️`, true);
                    bonusHitInSpin = true;

                    oneGRenOverlay.classList.add('visible');
                    setTimeout(() => {
                        oneGRenOverlay.classList.remove('visible');
                    }, 2000); // Show for 2 seconds
                    break;
                case 'KOYAKU_HIT':
                    if(!bonusHitInSpin) showMessage(`${event.name} +${event.payout}`);
                    break;
                case 'MIDDLE_CHERRY_HIT':
                    showMessage(`⚡️ MIDDLE CHERRY! ⚡️`, true);
                    break;
            }
        });
        // If bonus ended, turn off lamp unless another bonus started right after (1G-Ren)
        if (bonusEndInSpin && !bonusHitInSpin) {
            hibiscusImg.src = "images/hibiscus_off.svg";
            hibiscusImg.classList.remove('lit');
        }
        return bonusHitInSpin;
    }

    async function handleSpin() {
        if (player.credits < MEDALS_PER_SPIN) { return; }
        setButtonsDisabled(true);
        if (!gameState.is_in_bonus_at) {
            hibiscusImg.src = "images/hibiscus_off.svg";
            hibiscusImg.classList.remove('lit');
        }
        showMessage("Spinning...");

        player.credits -= MEDALS_PER_SPIN;
        
        await new Promise(resolve => setTimeout(resolve, 50));

        const result = spin(gameState);
        player.credits += result.payout;
        creditHistory.push({ x: gameState.total_games, y: player.credits });

        if (result.events.length === 0) {
            if(!gameState.is_in_bonus_at) showMessage("...");
        } else {
            processEvents(result.events);
        }

        updateUI();
        updateChart();
        setButtonsDisabled(false);
    }

    function handleSkip() {
        if (player.credits < MEDALS_PER_SPIN) { return; }
        setButtonsDisabled(true);
        hibiscusImg.src = "images/hibiscus_off.svg";
        hibiscusImg.classList.remove('lit');
        showMessage("Skipping to next bonus...");

        function runSkipLoop() {
            for (let i = 0; i < 1000; i++) {
                if (player.credits < MEDALS_PER_SPIN) {
                    showMessage("Not enough credits!");
                    updateUI();
                    updateChart();
                    // Keep buttons disabled
                    return;
                }
                player.credits -= MEDALS_PER_SPIN;
                const result = spin(gameState);
                player.credits += result.payout;
                creditHistory.push({ x: gameState.total_games, y: player.credits });

                const bonusStarted = result.events.some(e => e.event === 'BONUS_START' || e.event === '1G_REN');
                if (bonusStarted) {
                    processEvents(result.events);
                    updateUI();
                    updateChart();
                    setButtonsDisabled(false);
                    return; // Stop the loop
                }
            }
            // Update UI periodically during skip
            updateUI();
            setTimeout(runSkipLoop, 0); 
        }
        runSkipLoop();
    }

    function handleSkipAT() {
        if (!gameState.is_in_bonus_at) return;
        setButtonsDisabled(true);
        showMessage("Skipping AT...");

        function runATSkipLoop() {
            if (!gameState.is_in_bonus_at) {
                // Final update and re-enable buttons
                updateUI();
                updateChart();
                setButtonsDisabled(false);
                return;
            }

            // No credit cost for AT spins
            const result = spin(gameState);
            player.credits += result.payout;
            creditHistory.push({ x: gameState.total_games, y: player.credits });

            // Process events to handle 1G-ren queuing and bonus end
            processEvents(result.events);
            
            // Loop immediately
            setTimeout(runATSkipLoop, 0);
        }
        runATSkipLoop();
    }

    spinButton.addEventListener('click', handleSpin);
    skipButton.addEventListener('click', handleSkip);
    skipATButton.addEventListener('click', handleSkipAT);
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !spinButton.disabled) handleSpin();
    });

    updateUI();
    initializeChart();
});
