import random
import time
import sys
from collections import defaultdict

# --- ゲーム定数 (Version 2.3) ---

MEDALS_PER_SPIN = 3
NET_GAIN_PER_BONUS_GAME = 4.5
BONUS_PAYOUT_PER_GAME = NET_GAIN_PER_BONUS_GAME + MEDALS_PER_SPIN

BONUS_GAMES = {"BIG": 45, "REG": 18}

MIDDLE_CHERRY_PROB = 1 / 32768
KOYAKU = {
    "REPLAY":       {"prob": 1 / 7.3, "payout": MEDALS_PER_SPIN},
    "BELL":         {"prob": 1 / 12.2, "payout": 10},
    "WATERMELON":   {"prob": 1 / 143.7, "payout": 5},
    "CHERRY":       {"prob": 1 / 46.8, "payout": 3},
    "GUARANTEED":   {"prob": 1 / 4369.1, "payout": 0},
}
ONE_G_REN_PROB = {"CHERRY": 0.02, "WATERMELON": 0.06}
TENGOKU_UPGRADE_PROB = {
    "CHERRY": {"DOKI": 0.05, "SUPER_DOKI": 0.0},
    "WATERMELON": {"DOKI": 0.10, "SUPER_DOKI": 0.01},
}

SETTINGS = {
    1: {"bonus_prob": 1 / 240.0, "cherry_prob": 1 / 46.8, "name": "Setting 1"},
    2: {"bonus_prob": 1 / 230.2, "cherry_prob": 1 / 45.0, "name": "Setting 2"},
    3: {"bonus_prob": 1 / 215.8, "cherry_prob": 1 / 43.3, "name": "Setting 3"},
    5: {"bonus_prob": 1 / 192.1, "cherry_prob": 1 / 41.7, "name": "Setting 5"},
    6: {"bonus_prob": 1 / 181.0, "cherry_prob": 1 / 40.3, "name": "Setting 6"},
}

MODE_NORMAL_A, MODE_NORMAL_B, MODE_CHANCE = "Normal A", "Normal B", "Chance"
MODE_TENGOKU, MODE_DOKI_DOKI, MODE_SUPER_DOKI_DOKI = "Tengoku", "Doki Doki", "Super Doki Doki"
GAME_CEILING, THROUGH_CEILING = 800, 10

TENGOKU_PROB_TABLE = [p / sum([0.15]*5+[0.05]*5+[0.02]*10+[0.05]*5+[0.15]*7) * 1.1 for p in [0.15]*5+[0.05]*5+[0.02]*10+[0.05]*5+[0.15]*7]
MODE_TRANSITIONS = {
    MODE_NORMAL_A: {MODE_NORMAL_A: 0.53, MODE_NORMAL_B: 0.15, MODE_TENGOKU: 0.32},
    MODE_NORMAL_B: {MODE_NORMAL_B: 0.50, MODE_TENGOKU: 0.50},
    MODE_CHANCE:   {MODE_NORMAL_A: 0.40, MODE_TENGOKU: 0.60},
    MODE_TENGOKU:  {MODE_TENGOKU: 0.75, MODE_DOKI_DOKI: 0.05, MODE_NORMAL_A: 0.10, MODE_NORMAL_B: 0.10},
    MODE_DOKI_DOKI:{MODE_DOKI_DOKI: 0.78, MODE_SUPER_DOKI_DOKI: 0.20, MODE_NORMAL_A: 0.01, MODE_NORMAL_B: 0.01},
    MODE_SUPER_DOKI_DOKI: {MODE_SUPER_DOKI_DOKI: 0.94, MODE_NORMAL_A: 0.06},
}

class GameState:
    def __init__(self, setting_level=1, is_reset=True):
        self.setting = SETTINGS[setting_level]
        KOYAKU["CHERRY"]["prob"] = self.setting["cherry_prob"]
        self.total_games, self.total_payout, self.games_since_bonus = 0, 0, 0
        self.bonus_count, self.koyaku_counts, self.middle_cherry_hits = defaultdict(int), defaultdict(int), 0
        self.bonus_through_count, self.doki_doki_entries, self.super_doki_doki_entries = 0, 0, 0
        self.is_in_bonus_at, self.bonus_games_remaining, self.queued_1g_ren, self.middle_cherry_pending = False, 0, False, False
        if is_reset:
            rand = random.random()
            if rand < 0.50: self.current_mode = MODE_NORMAL_A
            elif rand < 0.602: self.current_mode = MODE_NORMAL_B
            else: self.current_mode = MODE_CHANCE
        else: self.current_mode = MODE_NORMAL_A
    def is_tengoku(self): return self.current_mode in [MODE_TENGOKU, MODE_DOKI_DOKI, MODE_SUPER_DOKI_DOKI]

def get_mode_transition(current_mode, source="NORMAL"):
    if source == "MIDDLE_CHERRY":
        rand = random.random()
        if rand < 0.55: return MODE_SUPER_DOKI_DOKI
        elif rand < 0.95: return MODE_DOKI_DOKI
        else: return MODE_TENGOKU
    transitions = MODE_TRANSITIONS.get(current_mode, {MODE_NORMAL_A: 1.0})
    rand, cumulative_prob = random.random(), 0
    for mode, prob in transitions.items():
        cumulative_prob += prob
        if rand < cumulative_prob: return mode
    return list(transitions.keys())[-1]

def start_bonus(state, bonus_type, verbose=True):
    state.bonus_count[bonus_type] += 1
    state.games_since_bonus = 0
    state.is_in_bonus_at = True
    state.bonus_games_remaining = BONUS_GAMES[bonus_type]

def handle_post_bonus(state, bonus_source="NORMAL", verbose=True):
    state.is_in_bonus_at = False
    if state.queued_1g_ren:
        state.queued_1g_ren = False
        start_bonus(state, "BIG", verbose)
        return
    previous_mode = state.current_mode
    new_mode = get_mode_transition(previous_mode, bonus_source)
    if new_mode == MODE_TENGOKU and bonus_source != "MIDDLE_CHERRY":
        promo_rand = random.random()
        if promo_rand < 0.005: new_mode = MODE_SUPER_DOKI_DOKI
        elif promo_rand < 0.08: new_mode = MODE_DOKI_DOKI
    if new_mode != previous_mode:
        state.current_mode = new_mode
        if new_mode == MODE_DOKI_DOKI: state.doki_doki_entries += 1
        elif new_mode == MODE_SUPER_DOKI_DOKI: state.super_doki_doki_entries += 1
    if state.is_tengoku(): state.bonus_through_count = 0
    else: state.bonus_through_count += 1

def spin(state, verbose=True):
    state.total_games += 1
    payout = 0
    bonus_source = "NORMAL"

    # --- 1. Bonus AT State ---
    if state.is_in_bonus_at:
        state.games_since_bonus = 0 # AT中は0にリセット
        state.bonus_games_remaining -= 1
        payout += BONUS_PAYOUT_PER_GAME

        # 1G連抽選
        rand, cumulative_prob = random.random(), 0
        for name in ["CHERRY", "WATERMELON"]:
            cumulative_prob += KOYAKU[name]["prob"]
            if rand < cumulative_prob:
                if random.random() < ONE_G_REN_PROB[name]:
                    state.queued_1g_ren = True
                break
        
        # ボーナス終了判定
        if state.bonus_games_remaining <= 0:
            handle_post_bonus(state, verbose=verbose)

    # --- 2. Normal State ---
    else:
        state.games_since_bonus += 1
        bonus_hit = False

        # 天井判定
        if state.is_tengoku() and state.games_since_bonus > 32:
            state.current_mode = MODE_NORMAL_A
            state.bonus_through_count = 1
        if state.games_since_bonus >= GAME_CEILING or state.bonus_through_count >= THROUGH_CEILING:
            bonus_hit = True
        
        # 成立役による抽選
        if not bonus_hit:
            # 中段チェリー
            if random.random() < MIDDLE_CHERRY_PROB:
                state.middle_cherry_hits += 1
                payout += 3 # チェリーとしての払い出し
                bonus_hit = True
                bonus_source = "MIDDLE_CHERRY"
            # 確定役
            elif random.random() < KOYAKU["GUARANTEED"]["prob"]:
                state.koyaku_counts["GUARANTEED"] += 1
                bonus_hit = True
            # 天国中
            elif state.is_tengoku() and state.games_since_bonus <= 32 and random.random() < TENGOKU_PROB_TABLE[state.games_since_bonus - 1]:
                bonus_hit = True
            # 通常時のボーナス確率
            else:
                prob = state.setting["bonus_prob"]
                # モード別確率補正 (仮)
                if random.random() < prob:
                    bonus_hit = True
        
        # 小役の払い出し
        if not bonus_hit:
            rand, cumulative_prob = random.random(), 0
            for name, data in KOYAKU.items():
                if name == "GUARANTEED": continue
                cumulative_prob += data["prob"]
                if rand < cumulative_prob:
                    payout += data["payout"]
                    state.koyaku_counts[name] += 1
                    # 天国中のモード昇格抽選
                    if state.is_tengoku() and name in TENGOKU_UPGRADE_PROB:
                        upgrade_rand = random.random()
                        if upgrade_rand < TENGOKU_UPGRADE_PROB[name]["SUPER_DOKI"]:
                            state.current_mode = MODE_SUPER_DOKI_DOKI
                            state.super_doki_doki_entries += 1
                        elif upgrade_rand < TENGOKU_UPGRADE_PROB[name]["DOKI"]:
                            state.current_mode = MODE_DOKI_DOKI
                            state.doki_doki_entries += 1
                    break
        
        # ボーナス当選時の処理
        if bonus_hit:
            if state.is_tengoku():
                big_ratio = 0.9
            elif state.current_mode in [MODE_NORMAL_A, MODE_NORMAL_B]:
                big_ratio = 0.6
            else:
                big_ratio = 0.7
            
            bonus_type = "BIG" if random.random() < big_ratio else "REG"
            start_bonus(state, bonus_type, verbose)
            # ここでボーナスゲームの1G目を消化しないように、これ以上の処理は行わない
    
    state.total_payout += payout
    return payout

def run_simulation(total_spins, setting_level):
    state = GameState(setting_level=setting_level)
    start_time = time.time()
    for i in range(total_spins):
        if (i + 1) % 1000000 == 0:
             print(f"  ... {i+1:,} games played ({time.time() - start_time:.2f}s)")
        spin(state, verbose=False)
    
    print(f"\n--- Setting {setting_level} Simulation Complete ({total_spins:,} games) ---")
    print(f"Calculated Payout Rate: {state.total_payout / (state.total_games * MEDALS_PER_SPIN):.2%}")
    doki_prob = state.total_games / state.doki_doki_entries if state.doki_doki_entries > 0 else 0
    super_doki_prob = state.total_games / state.super_doki_doki_entries if state.super_doki_doki_entries > 0 else 0
    print(f"Middle Cherry Hits: {state.middle_cherry_hits:,} (1 / {state.total_games / state.middle_cherry_hits if state.middle_cherry_hits > 0 else 0:,.0f})")
    print(f"Doki Doki Entry: {state.doki_doki_entries:,} times (1 / {doki_prob:,.0f})")
    print(f"Super Doki Doki Entry: {state.super_doki_doki_entries:,} times (1 / {super_doki_prob:,.0f})")

if __name__ == "__main__":
    for setting in sorted(SETTINGS.keys()):
        run_simulation(1_000_000, setting)
        print("\n" + "="*40 + "\n")