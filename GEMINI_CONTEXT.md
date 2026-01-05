# Project Context for Gemini Agent

This document provides a summary of the `okidoki-duo-simulator` project to quickly re-establish context for future development sessions.
**Note to Agent:** All terminal output and interactive responses from the agent will be in Japanese.

## 1. Project Overview

This project is a simulator for the pachislot machine "スマスロ沖ドキ！DUOアンコール". It has two main components:
1.  A **headless simulator** (`simulation_runner.py`) for running large-scale simulations to verify the payout rate (機械割).
2.  A **web-based UI** (`server.py` + `static/` files) for interactive, graphical play in a browser.

## 2. File Structure & Purpose

-   `/` (Root Directory)
    -   `GEMINI_CONTEXT.md`: **This file.** Provides context for the Gemini agent.
    -   `README.md`: The official user-facing documentation, including specs and how-to-run instructions.
    -   `server.py`: A simple Python web server to launch the Web UI. It accepts a setting level as a command-line argument.
    -   `simulation_runner.py`: The Python-based headless simulator for calculating payout rates. Accepts command-line arguments for settings and game count.

-   `/static/` (All frontend assets)
    -   `index.html`: The main HTML file for the UI layout.
    -   `style.css`: All CSS styles for the UI.
    -   `game.js`: **[CRITICAL]** Contains the **core game logic for the UI**, ported from Python. This includes all probabilities, mode transitions, and the `spin()` function.
    -   `script.js`: Handles UI events (button clicks), DOM manipulation, Chart.js integration, and calls functions in `game.js`.
    -   `/images/`: Contains the SVG files for the hibiscus lamp (`hibiscus_on.svg`, `hibiscus_off.svg`).

## 3. ❗ Critical Synchronization Note

The game logic exists in two separate places:
1.  `simulation_runner.py` (for high-speed simulation)
2.  `static/game.js` (for the Web UI)

**Any changes to game mechanics, probabilities, or core logic MUST be implemented in BOTH files to keep them synchronized.** Failure to do so will result in the UI behaving differently from the simulation.

## 4. Key Logic & Tweakable Parameters

To adjust game balance and payout rates, modify the following constant objects defined at the top of both `simulation_runner.py` and `static/game.js`:

-   `KOYAKU`: Probabilities and payouts for small wins (Bell, Replay, etc.). This primarily affects the "coin carry" (コイン持ち).
-   `SETTINGS`: Contains the base bonus probability and cherry probability for each of the 6 machine settings.
-   `MODE_TRANSITIONS`: A dictionary defining the (estimated) probabilities of moving between game modes after a bonus. This has the largest impact on the overall payout rate.
-   `TENGOKU_PROB_TABLE`: A weighted table for bonus probability during the 32 games of Tengoku mode.

## 5. Common Commands

-   **Run the Web UI (Setting 6):**
    ```bash
    python3 server.py 6
    ```
    Then open `http://localhost:8000` in a browser.

-   **Run the Payout Rate Simulation (Setting 1, 1M games):**
    ```bash
    python3 simulation_runner.py --simulate 1000000 1
    ```

## 6. GitHub Repository

-   **URL:** `https://github.com/Yuki-yamaguchi3847/okidoki-duo-simulator`

## 7. Current Development Status (As of 2026-01-05)

### Issue: Extremely Low Payout Rate in Simulation

A simulation of 1,000,000 games on Setting 6 resulted in a calculated payout rate of **86.59%**. This is significantly lower than the expected rate for this setting (which should be >100%), indicating a major discrepancy in the simulation parameters.

### Analysis & Primary Cause

An investigation into the simulation logic (`simulation_runner.py` and `static/game.js`) identified the following potential causes:

1.  **[Primary Cause] Incorrect Bonus Probability:** The `spin` function contains a hardcoded override that forces the bonus probability to `1/280.0` for `Normal A` mode and `1/260.0` for `Normal B` mode. This provisional code (`(仮)`) ignores the much higher probability defined in the `SETTINGS` object for the current setting (e.g., `1/181.0` for Setting 6). This is the main reason for the extremely low number of initial bonuses and the resulting low payout rate.

2.  **[Tuning Point] Low Tengoku Loop Rate:** The `MODE_TRANSITIONS` for `MODE_TENGOKU` define a 20% chance of falling out of a heaven mode after a bonus (`10% -> Normal A`, `10% -> Normal B`). This may be too high, suppressing the number of consecutive bonuses (`renchan`) and negatively impacting the payout rate. The real machine's loop rate might be higher (e.g., 85-90%).

3.  **[Tuning Point] Bonus Payouts:** The net gain per bonus game (`NET_GAIN_PER_BONUS_GAME`) is set to `4.5`. This value could be reviewed against real-world data if the payout rate is still off after fixing the primary cause.

### Next Steps

The immediate next step is to **fix the primary cause**. This involves removing the hardcoded bonus probability overrides in both `simulation_runner.py` and `static/game.js` to ensure the probabilities from the `SETTINGS` object are used correctly. After this fix, another simulation should be run to get a more accurate payout rate.
