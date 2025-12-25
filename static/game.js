// --- Game Constants (Version 2.1 - JS) ---
const MEDALS_PER_SPIN = 3;
const BONUS_PAYOUT = { "BIG": 204, "REG": 84 };

const KOYAKU = {
    "REPLAY":       { prob: 1 / 7.2, payout: MEDALS_PER_SPIN },
    "BELL":         { prob: 1 / 8.2, payout: 10 }, // Adjusted
    "WATERMELON":   { prob: 1 / 143.7, payout: 5 },
    "CHERRY":       { prob: 1 / 46.8, payout: 3 },
    "GUARANTEED":   { prob: 1 / 4369.1, payout: 0 },
};

const SETTINGS = {
    1: { bonus_prob: 1 / 240.0, cherry_prob: 1 / 46.8, name: "Setting 1", payout_rate: 0.972 },
    // ... other settings
    6: { bonus_prob: 1 / 181.0, cherry_prob: 1 / 40.3, name: "Setting 6", payout_rate: 1.10 },
};

// Game Modes
const MODE_NORMAL_A = "Normal A";
const MODE_NORMAL_B = "Normal B";
const MODE_CHANCE = "Chance";
const MODE_TENGOKU = "Tengoku";
const MODE_DOKI_DOKI = "Doki Doki";
const MODE_SUPER_DOKI_DOKI = "Super Doki Doki";
const MODE_DUO = "DUO";

// Ceilings
const GAME_CEILING = 800;
const THROUGH_CEILING = 10;

let TENGOKU_PROB_TABLE = [0.15, 0.15, 0.15, 0.15, 0.15, 0.05, 0.05, 0.05, 0.05, 0.05, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.05, 0.05, 0.05, 0.05, 0.05, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15];
const sum = TENGOKU_PROB_TABLE.reduce((a, b) => a + b, 0);
TENGOKU_PROB_TABLE = TENGOKU_PROB_TABLE.map(p => (p / sum) * 1.1);

// Estimated Mode Transitions (Adjusted)
const MODE_TRANSITIONS = {
    [MODE_NORMAL_A]: { [MODE_NORMAL_A]: 0.53, [MODE_NORMAL_B]: 0.15, [MODE_TENGOKU]: 0.32 },
    [MODE_NORMAL_B]: { [MODE_NORMAL_B]: 0.50, [MODE_TENGOKU]: 0.50 },
    [MODE_CHANCE]:   { [MODE_NORMAL_A]: 0.40, [MODE_TENGOKU]: 0.60 },
    [MODE_TENGOKU]:  { [MODE_TENGOKU]: 0.75, [MODE_DOKI_DOKI]: 0.05, [MODE_NORMAL_A]: 0.10, [MODE_NORMAL_B]: 0.10 },
    [MODE_DOKI_DOKI]:{ [MODE_DOKI_DOKI]: 0.80, [MODE_SUPER_DOKI_DOKI]: 0.02, [MODE_NORMAL_A]: 0.09, [MODE_NORMAL_B]: 0.09 },
    [MODE_DUO]:      { [MODE_DUO]: 0.80, [MODE_NORMAL_A]: 0.20 },
};

// --- Classes ---
class GameState {
    constructor(setting_level = 1, is_reset = true) {
        this.setting = SETTINGS[setting_level];
        KOYAKU["CHERRY"]["prob"] = this.setting["cherry_prob"];

        this.total_games = 0;
        this.total_payout = 0;
        this.games_since_bonus = 0;
        this.bonus_count = {};
        this.koyaku_counts = {};
        this.bonus_through_count = 0;

        if (is_reset) {
            const rand = Math.random();
            if (rand < 0.50) { this.current_mode = MODE_NORMAL_A; }
            else if (rand < 0.602) { this.current_mode = MODE_NORMAL_B; }
            else { this.current_mode = MODE_CHANCE; }
        } else {
            this.current_mode = MODE_NORMAL_A;
        }
    }

    is_tengoku() {
        return [MODE_TENGOKU, MODE_DOKI_DOKI, MODE_SUPER_DOKI_DOKI].includes(this.current_mode);
    }
}

// --- Core Functions ---
function get_mode_transition(current_mode) {
    const transitions = MODE_TRANSITIONS[current_mode] || { [MODE_NORMAL_A]: 1.0 };
    const rand = Math.random();
    let cumulative_prob = 0;
    for (const mode in transitions) {
        cumulative_prob += transitions[mode];
        if (rand < cumulative_prob) {
            return mode;
        }
    }
    return Object.keys(transitions).pop();
}

function play_bonus(state) {
    const bonus_type = Math.random() < 0.7 ? "BIG" : "REG";
    const payout = BONUS_PAYOUT[bonus_type];
    
    state.bonus_count[bonus_type] = (state.bonus_count[bonus_type] || 0) + 1;
    state.games_since_bonus = 0;

    const new_mode = get_mode_transition(state.current_mode);
    const mode_changed = new_mode !== state.current_mode;
    state.current_mode = new_mode;
    
    if (state.is_tengoku()) {
        state.bonus_through_count = 0;
    } else {
        state.bonus_through_count += 1;
    }
    
    return { bonus_type, payout, mode_changed, new_mode };
}

function spin(state) {
    state.total_games += 1;
    state.games_since_bonus += 1;

    // *** BUG FIX: Add Tengoku timeout logic ***
    if (state.is_tengoku() && state.games_since_bonus > 32) {
        state.current_mode = MODE_NORMAL_A;
        state.bonus_through_count = 1;
    }

    let payout = 0;
    let bonus_hit = false;
    let bonus_info = null;
    let hit_koyaku = null;
    let message = "";

    // 1. Ceiling Check
    if (state.games_since_bonus >= GAME_CEILING || state.bonus_through_count >= THROUGH_CEILING) {
        message = "Ceiling reached! Guaranteed bonus!";
        bonus_hit = true;
    }
    // 2. Tengoku Mode Bonus Check
    else if (state.is_tengoku() && state.games_since_bonus <= 32) {
        if (Math.random() < TENGOKU_PROB_TABLE[state.games_since_bonus - 1]) {
            message = "Tengoku Bonus!";
            bonus_hit = true;
        }
    }
    // 3. Guaranteed Win Check
    else if (Math.random() < KOYAKU["GUARANTEED"]["prob"]) {
        message = "Guaranteed Win Hit!";
        state.koyaku_counts["GUARANTEED"] = (state.koyaku_counts["GUARANTEED"] || 0) + 1;
        bonus_hit = true;
    }
    // 4. Standard Bonus Check
    else if (Math.random() < state.setting["bonus_prob"]) {
        message = "Bonus Hit!";
        bonus_hit = true;
    }
    
    // 5. Small Win Check
    if (!bonus_hit) {
        const rand = Math.random();
        let cumulative_prob = 0;
        for (const name in KOYAKU) {
            if (name === "GUARANTEED") continue;
            cumulative_prob += KOYAKU[name]["prob"];
            if (rand < cumulative_prob) {
                payout += KOYAKU[name]["payout"];
                state.koyaku_counts[name] = (state.koyaku_counts[name] || 0) + 1;
                hit_koyaku = name;
                break;
            }
        }
    }
    
    // Payout for the spin itself is added to total_payout here.
    // Bonus payouts are added within play_bonus.
    state.total_payout += payout;

    if (bonus_hit) {
        const gamesFromPreviousBonus = state.games_since_bonus; // Capture BEFORE play_bonus resets it
        bonus_info = play_bonus(state);
        bonus_info.gamesFromPreviousBonus = gamesFromPreviousBonus; // Add to info
        // Bonus payout is now added inside play_bonus, so we just add it to the spin payout for the return value
        payout += bonus_info.payout;
    }
        
    return { payout, bonus_info, hit_koyaku, message };
}
