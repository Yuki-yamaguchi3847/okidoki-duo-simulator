# Project Context for Gemini Agent

This document provides a summary of the `okidoki-duo-simulator` project (v2.4) to quickly re-establish context for future development sessions.
**Note to Agent:** All terminal output and interactive responses from the agent will be in Japanese.

## 1. Project Overview

This project is a simulator for the pachislot machine "スマスロ沖ドキ！DUOアンコール". It has two main components:
1.  A **headless simulator** (`simulation_runner.py`) for running large-scale simulations to verify the payout rate (機械割).
2.  A **web-based UI** (`server.py` + `static/` files) for interactive, graphical play in a browser.
3.  A **terminal-based graph simulator** (`terminal_graph_simulator.py`) for running simulations and visualizing credit history and other statistics directly in the terminal.

## 2. File Structure & Purpose

-   `/` (Root Directory)
    -   `GEMINI_CONTEXT.md`: **This file.** Provides context for the Gemini agent.
    -   `README.md`: The official user-facing documentation, including specs and how-to-run instructions.
    -   `server.py`: A Python web server that launches the Web UI. It dynamically generates a `/config.js` file to pass the selected setting level to the frontend.
    -   `simulation_runner.py`: The Python-based headless simulator. It only runs in batch simulation mode (`--simulate`); interactive mode is disabled.
    -   `terminal_graph_simulator.py`: A Python script that runs simulations and displays credit history graphs and statistics in the terminal. Requires the `plotext` library.

-   `/static/` (All frontend assets)
    -   `index.html`: The main HTML file for the UI layout.
    -   `style.css`: All CSS styles for the UI.
    -   `game.js`: **[CRITICAL]** Contains the **core game logic for the UI**, ported from Python. This includes all probabilities, mode transitions, and the `spin()` function.
    -   `script.js`: Handles UI events (button clicks), DOM manipulation, Chart.js integration, and calls functions in `game.js`.
    -   `config.js`: **[Generated File]** This file is created dynamically by `server.py` and is not in the repository. It contains the `SETTING_LEVEL` JavaScript constant.
    -   `/images/`: Contains the SVG files for the hibiscus lamp (`hibiscus_on.svg`, `hibiscus_off.svg`).

## 3. ❗ Critical Synchronization Note

The game logic exists in multiple places:
1.  `simulation_runner.py` (for high-speed simulation)
2.  `static/game.js` (for the Web UI)
3.  `terminal_graph_simulator.py` (for terminal graph simulation)

**Any changes to game mechanics, probabilities, or core logic MUST be implemented in ALL relevant files to keep them synchronized.**

## 4. Key Logic & Tweakable Parameters

To adjust game balance and payout rates, modify the constant objects defined at the top of relevant simulation files:

-   `KOYAKU`: Probabilities and payouts for small wins.
-   `SETTINGS`: Contains the base bonus probability and cherry probability for each machine setting.
-   `MODE_TRANSITIONS`: Defines the probabilities of moving between game modes after a bonus.
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
-   **Run the Terminal Graph Simulation (Setting 6, 10K games):**
    ```bash
    python3 terminal_graph_simulator.py 10000 6
    ```
    (Requires `plotext` library. Install with `pip install plotext`.)

## 6. GitHub Repository

-   **URL:** `https://github.com/Yuki-yamaguchi3847/okidoki-duo-simulator`

## 7. Current Development Status (As of 2026-01-06)

### Status: Payout Rate Issue Resolved

The previous major issue causing an extremely low payout rate (e.g., ~87% on Setting 6) has been **resolved**.

### Analysis of the Fix

The primary cause of the low payout rate was a hardcoded bonus probability in the `spin` function of both `simulation_runner.py` and `static/game.js`. This code, intended as a temporary measure (`(仮)`), overrode the correct probabilities defined in the `SETTINGS` object.

**The fix involved removing this hardcoded logic.** The simulation now correctly uses the `bonus_prob` from the `SETTINGS` object for the selected setting level. As a result, a test simulation for Setting 6 now yields a much more realistic payout rate.

### Recent Enhancements

-   **Terminal Graph Simulator:** Added `terminal_graph_simulator.py` for visualizing credit history and displaying statistics (including max renchan count/payout and final medal count) directly in the terminal.
-   **Max Renchan Tracking:** The `terminal_graph_simulator.py` now tracks and reports the maximum consecutive bonus streak and the maximum payout obtained from a single streak.
-   **Final Medal Count:** The `terminal_graph_simulator.py` now displays the final medal count at the end of the simulation.
-   **`WATERMELON` Probability Correction:** Corrected a bug in `terminal_graph_simulator.py` where the `WATERMELON` probability was incorrectly set (was 1/14.7, corrected to 1/143.7).

### Next Steps

The core logic is now considered stable. Future work can focus on:
-   Further fine-tuning of `MODE_TRANSITIONS` or other parameters to match official payout rates with even higher precision.
-   Adding new features to the Web UI.
-   Refactoring or code cleanup.
