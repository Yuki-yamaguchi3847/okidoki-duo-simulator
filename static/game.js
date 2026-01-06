// --- Game Constants (Version 2.3 - JS) ---
const MEDALS_PER_SPIN = 3;
const NET_GAIN_PER_BONUS_GAME = 4.5;
const BONUS_PAYOUT_PER_GAME = NET_GAIN_PER_BONUS_GAME + MEDALS_PER_SPIN;
const BONUS_GAMES = { "BIG": 45, "REG": 18 };

const MIDDLE_CHERRY_PROB = 1 / 32768;
const KOYAKU = {
    "REPLAY": { prob: 1 / 7.3, payout: MEDALS_PER_SPIN },
    "BELL": { prob: 1 / 12.2, payout: 10 },
    "WATERMELON": { prob: 1 / 143.7, payout: 5 },
    "CHERRY": { prob: 1 / 46.8, payout: 3 },
    "GUARANTEED": { prob: 1 / 4369.1, payout: 0 },
};
const ONE_G_REN_PROB = { "CHERRY": 0.02, "WATERMELON": 0.06 };
const TENGOKU_UPGRADE_PROB = {
    "CHERRY": { "DOKI": 0.05, "SUPER_DOKI": 0.0 },
    "WATERMELON": { "DOKI": 0.10, "SUPER_DOKI": 0.01 },
};

const SETTINGS = {
    1: { bonus_prob: 1 / 240.0, cherry_prob: 1 / 46.8, name: "Setting 1" },
    6: { bonus_prob: 1 / 181.0, cherry_prob: 1 / 40.3, name: "Setting 6" },
};

const MODE_NORMAL_A = "Normal A", MODE_NORMAL_B = "Normal B", MODE_CHANCE = "Chance";
const MODE_TENGOKU = "Tengoku", MODE_DOKI_DOKI = "Doki Doki", MODE_SUPER_DOKI_DOKI = "Super Doki Doki";
const GAME_CEILING = 800, THROUGH_CEILING = 10;

const TENGOKU_PROB_TABLE = (() => {
    const table = [0.15, 0.15, 0.15, 0.15, 0.15, 0.05, 0.05, 0.05, 0.05, 0.05, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.05, 0.05, 0.05, 0.05, 0.05, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15];
    const sum = table.reduce((a, b) => a + b, 0);
    return table.map(p => (p / sum) * 1.1);
})();

const MODE_TRANSITIONS = {
    [MODE_NORMAL_A]: { [MODE_NORMAL_A]: 0.53, [MODE_NORMAL_B]: 0.15, [MODE_TENGOKU]: 0.32 },
    [MODE_NORMAL_B]: { [MODE_NORMAL_B]: 0.50, [MODE_TENGOKU]: 0.50 },
    [MODE_CHANCE]: { [MODE_NORMAL_A]: 0.40, [MODE_TENGOKU]: 0.60 },
    [MODE_TENGOKU]: { [MODE_TENGOKU]: 0.75, [MODE_DOKI_DOKI]: 0.05, [MODE_NORMAL_A]: 0.10, [MODE_NORMAL_B]: 0.10 },
    [MODE_DOKI_DOKI]: { [MODE_DOKI_DOKI]: 0.78, [MODE_SUPER_DOKI_DOKI]: 0.20, [MODE_NORMAL_A]: 0.01, [MODE_NORMAL_B]: 0.01 },
    [MODE_SUPER_DOKI_DOKI]: { [MODE_SUPER_DOKI_DOKI]: 0.94, [MODE_NORMAL_A]: 0.06 },
};

class GameState {
    constructor(setting_level = 1, is_reset = true) {
        this.setting = SETTINGS[setting_level];
        KOYAKU["CHERRY"]["prob"] = this.setting["cherry_prob"];
        this.total_games = 0; this.total_payout = 0; this.games_since_bonus = 0;
        this.renchan_count = 0; this.renchan_payout = 0;
        this.bonus_count = {}; this.koyaku_counts = {}; this.middle_cherry_hits = 0;
        this.bonus_through_count = 0; this.doki_doki_entries = 0; this.super_doki_doki_entries = 0;
        this.is_in_bonus_at = false; this.bonus_games_remaining = 0; this.queued_1g_ren = false; this.middle_cherry_pending = false;
        this.current_bonus_type = null;
        if (is_reset) {
            const rand = Math.random();
            if (rand < 0.50) this.current_mode = MODE_NORMAL_A;
            else if (rand < 0.602) this.current_mode = MODE_NORMAL_B;
            else this.current_mode = MODE_CHANCE;
        } else {
            this.current_mode = MODE_NORMAL_A;
        }
    }
    is_tengoku() { return [MODE_TENGOKU, MODE_DOKI_DOKI, MODE_SUPER_DOKI_DOKI].includes(this.current_mode); }
}

function get_mode_transition(current_mode, source = "NORMAL") {
    if (source === "MIDDLE_CHERRY") {
        const rand = Math.random();
        if (rand < 0.55) return MODE_SUPER_DOKI_DOKI;
        if (rand < 0.95) return MODE_DOKI_DOKI;
        return MODE_TENGOKU;
    }
    const transitions = MODE_TRANSITIONS[current_mode] || { [MODE_NORMAL_A]: 1.0 };
    const rand = Math.random();
    let cumulative_prob = 0;
    for (const mode in transitions) {
        cumulative_prob += transitions[mode];
        if (rand < cumulative_prob) return mode;
    }
    return Object.keys(transitions).pop();
}

function start_bonus(state, bonus_type, bonus_source = "NORMAL") {
    if (state.is_tengoku()) {
        if (state.renchan_count === 0) {
            state.renchan_payout = 0;
        }
        state.renchan_count++;
    }
    const games_since = state.games_since_bonus; // リセット前に値を保持
    state.bonus_count[bonus_type] = (state.bonus_count[bonus_type] || 0) + 1;
    state.games_since_bonus = 0;
    state.is_in_bonus_at = true;
    state.current_bonus_type = bonus_type;
    state.bonus_games_remaining = BONUS_GAMES[bonus_type];
    return { event: 'BONUS_START', type: bonus_type, games: state.bonus_games_remaining, games_since_bonus: games_since };
}

function handle_post_bonus(state, bonus_source = "NORMAL") {
    state.is_in_bonus_at = false;
    let eventInfo = { event: 'BONUS_END' };
    const was_tengoku = state.is_tengoku();

    if (state.queued_1g_ren) {
        state.queued_1g_ren = false;
        state.games_since_bonus = 1; // 1G連の場合はゲーム数を1に設定
        Object.assign(eventInfo, start_bonus(state, "BIG"));
        eventInfo.event = '1G_REN';
        return eventInfo;
    }
    const previous_mode = state.current_mode;
    let new_mode = get_mode_transition(previous_mode, bonus_source);
    if (new_mode === MODE_TENGOKU && bonus_source !== "MIDDLE_CHERRY") {
        const promo_rand = Math.random();
        if (promo_rand < 0.005) new_mode = MODE_SUPER_DOKI_DOKI;
        else if (promo_rand < 0.08) new_mode = MODE_DOKI_DOKI;
    }
    if (new_mode !== previous_mode) {
        if (new_mode === MODE_DOKI_DOKI) state.doki_doki_entries++;
        else if (new_mode === MODE_SUPER_DOKI_DOKI) state.super_doki_doki_entries++;
    }
    state.current_mode = new_mode;

    if (was_tengoku && !state.is_tengoku()) {
        eventInfo.renchan_streak_ended = true;
        eventInfo.renchan_count = state.renchan_count;
        eventInfo.renchan_payout = state.renchan_payout;
        state.renchan_count = 0;
        state.renchan_payout = 0;
    }

    if (state.is_tengoku()) state.bonus_through_count = 0;
    else state.bonus_through_count++;
    eventInfo.mode_changed_to = state.current_mode;
    return eventInfo;
}

function spin(state) {
    state.total_games++;
    let payout = 0, events = [], bonus_source = "NORMAL";

    // --- 1. Bonus AT State ---
    if (state.is_in_bonus_at) {
        state.games_since_bonus = 0; // AT中は0
        state.bonus_games_remaining--;
        payout += BONUS_PAYOUT_PER_GAME;

        if (state.renchan_count > 0) {
            state.renchan_payout += BONUS_PAYOUT_PER_GAME;
        }

        // 1G連抽選
        const rand = Math.random();
        let cumulative_prob = 0;
        for (const name of ["CHERRY", "WATERMELON"]) {
            cumulative_prob += KOYAKU[name]["prob"];
            if (rand < cumulative_prob) {
                if (Math.random() < ONE_G_REN_PROB[name]) {
                    state.queued_1g_ren = true;
                    events.push({event: '1G_REN_QUEUED', role: name});
                }
                break;
            }
        }
        
        // ボーナス終了判定
        if (state.bonus_games_remaining <= 0) {
            events.push(handle_post_bonus(state));
        }
    }
    // --- 2. Normal State ---
    else {
        state.games_since_bonus++;
        let bonus_hit = false;

        // 天井判定
        if (state.is_tengoku() && state.games_since_bonus > 32) {
            if (state.renchan_count > 0) {
                events.push({
                    event: 'RENCHAN_STREAK_END',
                    reason: 'Tengoku抜け',
                    renchan_count: state.renchan_count,
                    renchan_payout: state.renchan_payout
                });
                state.renchan_count = 0;
                state.renchan_payout = 0;
            }
            state.current_mode = MODE_NORMAL_A;
            state.bonus_through_count = 1;
            events.push({event: 'MODE_CHANGE', to: MODE_NORMAL_A, reason: 'Tengoku抜け'});
        }
        if (state.games_since_bonus >= GAME_CEILING || state.bonus_through_count >= THROUGH_CEILING) {
            bonus_hit = true;
            events.push({event: 'CEILING_HIT', type: state.games_since_bonus >= GAME_CEILING ? 'GAME' : 'THROUGH'});
        }

        // 成立役による抽選
        if (!bonus_hit) {
            // 中段チェリー
            if (Math.random() < MIDDLE_CHERRY_PROB) {
                state.middle_cherry_hits++;
                payout += 3;
                bonus_hit = true;
                bonus_source = "MIDDLE_CHERRY";
                events.push({event: 'MIDDLE_CHERRY_HIT'});
            // 確定役
            } else if (Math.random() < KOYAKU["GUARANTEED"]["prob"]) {
                state.koyaku_counts["GUARANTEED"] = (state.koyaku_counts["GUARANTEED"] || 0) + 1;
                bonus_hit = true;
                events.push({event: 'KOYAKU_HIT', name: 'GUARANTEED'});
            // 天国中
            } else if (state.is_tengoku() && state.games_since_bonus <= 32 && Math.random() < TENGOKU_PROB_TABLE[state.games_since_bonus - 1]) {
                bonus_hit = true;
            // 通常時のボーナス確率
            } else {
                let prob = state.setting["bonus_prob"];
                if (Math.random() < prob) {
                    bonus_hit = true;
                }
            }
        }

        // 小役の払い出し
        if (!bonus_hit) {
            const rand = Math.random();
            let cumulative_prob = 0;
            for (const name in KOYAKU) {
                if (name === "GUARANTEED") continue;
                cumulative_prob += KOYAKU[name]["prob"];
                if (rand < cumulative_prob) {
                    payout += KOYAKU[name]["payout"];
                    state.koyaku_counts[name] = (state.koyaku_counts[name] || 0) + 1;
                    events.push({event: 'KOYAKU_HIT', name: name, payout: KOYAKU[name]["payout"]});
                    
                    // 天国中のモード昇格抽選
                    if (state.is_tengoku() && TENGOKU_UPGRADE_PROB[name]) {
                        const upgrade_rand = Math.random();
                        if (upgrade_rand < TENGOKU_UPGRADE_PROB[name]["SUPER_DOKI"]) {
                            state.current_mode = MODE_SUPER_DOKI_DOKI;
                            state.super_doki_doki_entries++;
                            events.push({event: 'MODE_UPGRADE', to: MODE_SUPER_DOKI_DOKI});
                        } else if (upgrade_rand < TENGOKU_UPGRADE_PROB[name]["DOKI"]) {
                            state.current_mode = MODE_DOKI_DOKI;
                            state.doki_doki_entries++;
                            events.push({event: 'MODE_UPGRADE', to: MODE_DOKI_DOKI});
                        }
                    }
                    break;
                }
            }
        }

        // ボーナス当選時の処理
        if (bonus_hit) {
            let big_ratio;
            if (state.is_tengoku()) {
                big_ratio = 0.9;
            } else if (state.current_mode === MODE_NORMAL_A || state.current_mode === MODE_NORMAL_B) {
                big_ratio = 0.6;
            } else {
                big_ratio = 0.7;
            }
            const bonus_type = Math.random() < big_ratio ? "BIG" : "REG";
            events.push(start_bonus(state, bonus_type, bonus_source));
        }
    }
    state.total_payout += payout;
    return { payout, events };
}
