document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const creditsEl = document.getElementById('credits');
    const modeEl = document.getElementById('current-mode');
    const gamesSinceBonusEl = document.getElementById('games-since-bonus');
    const totalGamesEl = document.getElementById('total-games');
    const spinButton = document.getElementById('spin-button');
    const skipButton = document.getElementById('skip-button');
    const hibiscusImg = document.getElementById('hibiscus-img');
    const messageLog = document.getElementById('last-action-message');
    const bonusHistoryLogEl = document.getElementById('bonus-history-log');
    const chartCanvas = document.getElementById('credit-chart');

    // --- Game and History Initialization ---
    let player = { credits: 1000 };
    let gameState = new GameState(typeof SETTING_LEVEL !== 'undefined' ? SETTING_LEVEL : 1, true);
    
    let creditHistory = [{x: 0, y: 1000}];
    let bonusHistory = [];
    let creditChart;

    // --- Chart.js Initialization ---
    function initializeChart() {
        const ctx = chartCanvas.getContext('2d');
        creditChart = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Credits',
                    data: creditHistory,
                    borderColor: '#ffc107',
                    backgroundColor: 'rgba(255, 193, 7, 0.1)',
                    borderWidth: 2,
                    tension: 0.1,
                    pointRadius: 0,
                }]
            },
            options: {
                animation: false,
                scales: {
                    x: {
                        type: 'linear',
                        title: { display: true, text: 'Total Games', color: '#aaa' },
                        ticks: { color: '#aaa' },
                        grid: { color: 'rgba(255, 255, 255, 0.1)' }
                    },
                    y: {
                        title: { display: true, text: 'Credits', color: '#aaa' },
                        ticks: { color: '#aaa' },
                        grid: { color: 'rgba(255, 255, 255, 0.1)' }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    function updateChart() {
        creditChart.data.labels = creditHistory.map(d => d.x);
        creditChart.data.datasets[0].data = creditHistory.map(d => d.y);
        creditChart.update('none'); // 'none' for no animation
    }

    function addBonusToLog(bonusInfo) {
        const li = document.createElement('li');
        const bonusClass = bonusInfo.bonus_type === 'BIG' ? 'bonus-big' : 'bonus-reg';
        li.innerHTML = `
            <span class="${bonusClass}">${bonusInfo.bonus_type}</span> at game ${gameState.total_games}
            (${bonusInfo.gamesFromPreviousBonus}G, Mode: ${bonusInfo.new_mode})
        `;
        bonusHistoryLogEl.prepend(li);
    }
    
    function updateUI() {
        creditsEl.textContent = player.credits;
        modeEl.textContent = gameState.current_mode;
        gamesSinceBonusEl.textContent = gameState.games_since_bonus;
        totalGamesEl.textContent = gameState.total_games;
    }

    function showMessage(msg, isBonus = false) {
        messageLog.textContent = msg;
        if (isBonus) {
            messageLog.style.color = "#ff4848";
        } else {
            messageLog.style.color = "#ffc107";
        }
    }

    function setButtonsDisabled(disabled) {
        spinButton.disabled = disabled;
        skipButton.disabled = disabled;
    }

    // --- Spin Logic Handlers ---
    async function handleSpin() {
        if (player.credits < MEDALS_PER_SPIN) {
            showMessage("Not enough credits!");
            setButtonsDisabled(true);
            return;
        }

        setButtonsDisabled(true);
        hibiscusImg.src = "images/hibiscus_off.svg";
        hibiscusImg.classList.remove('lit');
        showMessage("Spinning...");

        player.credits -= MEDALS_PER_SPIN;
        
        await new Promise(resolve => setTimeout(resolve, 100));

        const result = spin(gameState);
        player.credits += result.payout;

        creditHistory.push({ x: gameState.total_games, y: player.credits });

        if (result.bonus_info) {
            hibiscusImg.src = "images/hibiscus_on.svg";
            hibiscusImg.classList.add('lit');
            const { bonus_type, payout } = result.bonus_info;
            showMessage(`🎉 ${bonus_type} BONUS! +${payout} 🎉`, true);
            addBonusToLog(result.bonus_info);
        } else if (result.hit_koyaku) {
             showMessage(`${result.hit_koyaku} +${result.payout}`);
        } else {
            showMessage("...");
        }

        updateUI();
        updateChart();
        setButtonsDisabled(false);
    }

    function handleSkip() {
        if (player.credits < MEDALS_PER_SPIN) {
            showMessage("Not enough credits!");
            setButtonsDisabled(true);
            return;
        }

        setButtonsDisabled(true);
        hibiscusImg.src = "images/hibiscus_off.svg";
        hibiscusImg.classList.remove('lit');
        showMessage("Skipping to next bonus...");

        let bonusFound = false;
        let gamesInBatch = 0;
        
        function runSkipLoop() {
            for (let i = 0; i < 200; i++) { // Run in larger batches
                if (player.credits < MEDALS_PER_SPIN) {
                    showMessage("Not enough credits!");
                    bonusFound = true; // To stop the loop
                    break;
                }

                player.credits -= MEDALS_PER_SPIN;
                const result = spin(gameState);
                player.credits += result.payout;
                
                // Add data point for every spin
                creditHistory.push({ x: gameState.total_games, y: player.credits });

                if (result.bonus_info) {
                    hibiscusImg.src = "images/hibiscus_on.svg";
                    hibiscusImg.classList.add('lit');
                    const { bonus_type, payout } = result.bonus_info;
                    showMessage(`🎉 SKIPPED TO ${bonus_type} BONUS! +${payout} 🎉`, true);
                    addBonusToLog(result.bonus_info);
                    bonusFound = true;
                    break;
                }
            }

            if (bonusFound) {
                updateUI();
                updateChart();
                setButtonsDisabled(false);
            } else {
                updateUI(); // Update stats periodically
                setTimeout(runSkipLoop, 0); 
            }
        }

        runSkipLoop();
    }

    // --- Event Listeners ---
    spinButton.addEventListener('click', handleSpin);
    skipButton.addEventListener('click', handleSkip);

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !spinButton.disabled) {
            handleSpin();
        }
    });

    // --- Initial UI setup ---
    updateUI();
    initializeChart();
});
