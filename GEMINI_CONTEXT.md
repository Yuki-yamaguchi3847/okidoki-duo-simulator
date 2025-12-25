# Project Context for Gemini Agent

This document provides a summary of the `okidoki-duo-simulator` project to quickly re-establish context for future development sessions.

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
