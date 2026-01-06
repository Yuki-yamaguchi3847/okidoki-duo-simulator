import random
import time
import sys
from collections import defaultdict

# このスクリプトを実行するには、'plotext'ライブラリが必要です。
# インストールされていない場合は、ターミナルで以下のコマンドを実行してください:
# pip install plotext
try:
    import plotext as plt
except ImportError:
    print("エラー: 'plotext'ライブラリが見つかりません。")
    print("ターミナルで 'pip install plotext' を実行してインストールしてください。")
    sys.exit(1)

# --- ゲーム定数 (Version 2.4) ---

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
        
        # 連荘記録用の変数
        self.current_renchan_count = 0
        self.current_renchan_payout = 0
        self.max_renchan_count = 0
        self.max_renchan_payout = 0
        
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
    # 天国モード中のボーナス当選は連荘カウントを増やす
    if state.is_tengoku():
        state.current_renchan_count += 1
        
    state.bonus_count[bonus_type] += 1
    state.games_since_bonus = 0
    state.is_in_bonus_at = True
    state.bonus_games_remaining = BONUS_GAMES[bonus_type]

def handle_post_bonus(state, bonus_source="NORMAL", verbose=True):
    state.is_in_bonus_at = False
    
    # 1G連の処理
    if state.queued_1g_ren:
        state.queued_1g_ren = False
        start_bonus(state, "BIG", verbose)
        return

    previous_mode_was_tengoku = state.is_tengoku()
    previous_mode = state.current_mode
    new_mode = get_mode_transition(previous_mode, bonus_source)

    if new_mode == MODE_TENGOKU and bonus_source != "MIDDLE_CHERRY":
        promo_rand = random.random()
        if promo_rand < 0.005: new_mode = MODE_SUPER_DOKI_DOKI
        elif promo_rand < 0.08: new_mode = MODE_DOKI_DOKI

    state.current_mode = new_mode
    if new_mode != previous_mode:
        if new_mode == MODE_DOKI_DOKI: state.doki_doki_entries += 1
        elif new_mode == MODE_SUPER_DOKI_DOKI: state.super_doki_doki_entries += 1

    # 連荘状態の管理
    is_now_tengoku = state.is_tengoku()
    if previous_mode_was_tengoku and not is_now_tengoku:
        # 天国から転落した場合、連荘記録を更新
        if state.current_renchan_count > state.max_renchan_count:
            state.max_renchan_count = state.current_renchan_count
            state.max_renchan_payout = state.current_renchan_payout
        # 連荘情報をリセット
        state.current_renchan_count = 0
        state.current_renchan_payout = 0
    elif not previous_mode_was_tengoku and is_now_tengoku:
        # 通常から天国へ昇格した場合、連荘カウントを1から開始
        state.current_renchan_count = 1
        state.current_renchan_payout = 0

    if state.is_tengoku(): state.bonus_through_count = 0
    else: state.bonus_through_count += 1

def spin(state, verbose=True):
    state.total_games += 1
    payout = 0
    bonus_source = "NORMAL"

    if state.is_in_bonus_at:
        state.games_since_bonus = 0
        state.bonus_games_remaining -= 1
        payout += BONUS_PAYOUT_PER_GAME
        # 連荘中の場合、獲得枚数を加算
        if state.current_renchan_count > 0:
            state.current_renchan_payout += BONUS_PAYOUT_PER_GAME

        rand, cumulative_prob = random.random(), 0
        for name in ["CHERRY", "WATERMELON"]:
            cumulative_prob += KOYAKU[name]["prob"]
            if rand < cumulative_prob:
                if random.random() < ONE_G_REN_PROB[name]:
                    state.queued_1g_ren = True
                break
        
        if state.bonus_games_remaining <= 0:
            handle_post_bonus(state, verbose=verbose)
    else:
        previous_mode_was_tengoku = state.is_tengoku()
        state.games_since_bonus += 1
        bonus_hit = False

        if state.is_tengoku() and state.games_since_bonus > 32:
            state.current_mode = MODE_NORMAL_A
            state.bonus_through_count = 1
            # 天国抜けによる連荘終了
            if previous_mode_was_tengoku:
                if state.current_renchan_count > state.max_renchan_count:
                    state.max_renchan_count = state.current_renchan_count
                    state.max_renchan_payout = state.current_renchan_payout
                state.current_renchan_count = 0
                state.current_renchan_payout = 0

        if state.games_since_bonus >= GAME_CEILING or state.bonus_through_count >= THROUGH_CEILING:
            bonus_hit = True
        
        if not bonus_hit:
            if random.random() < MIDDLE_CHERRY_PROB:
                state.middle_cherry_hits += 1
                payout += 3
                bonus_hit = True
                bonus_source = "MIDDLE_CHERRY"
            elif random.random() < KOYAKU["GUARANTEED"]["prob"]:
                state.koyaku_counts["GUARANTEED"] += 1
                bonus_hit = True
            elif state.is_tengoku() and state.games_since_bonus <= 32 and random.random() < TENGOKU_PROB_TABLE[state.games_since_bonus - 1]:
                bonus_hit = True
            else:
                prob = state.setting["bonus_prob"]
                if random.random() < prob:
                    bonus_hit = True
        
        if not bonus_hit:
            rand, cumulative_prob = random.random(), 0
            for name, data in KOYAKU.items():
                if name == "GUARANTEED": continue
                cumulative_prob += data["prob"]
                if rand < cumulative_prob:
                    payout += data["payout"]
                    state.koyaku_counts[name] += 1
                    if state.is_tengoku() and name in TENGOKU_UPGRADE_PROB:
                        upgrade_rand = random.random()
                        if upgrade_rand < TENGOKU_UPGRADE_PROB[name]["SUPER_DOKI"]:
                            state.current_mode = MODE_SUPER_DOKI_DOKI
                            state.super_doki_doki_entries += 1
                        elif upgrade_rand < TENGOKU_UPGRADE_PROB[name]["DOKI"]:
                            state.current_mode = MODE_DOKI_DOKI
                            state.doki_doki_entries += 1
                    break
        
        if bonus_hit:
            big_ratio = 0.9 if state.is_tengoku() else (0.6 if state.current_mode in [MODE_NORMAL_A, MODE_NORMAL_B] else 0.7)
            bonus_type = "BIG" if random.random() < big_ratio else "REG"
            start_bonus(state, bonus_type, verbose)
    
    state.total_payout += payout - MEDALS_PER_SPIN
    return payout

def run_simulation(total_spins, setting_level):
    state = GameState(setting_level=setting_level)
    start_time = time.time()
    
    credit_history = [0]
    print(f"シミュレーションを開始します... (設定: {setting_level}, ゲーム数: {total_spins:,})")
    
    for i in range(total_spins):
        if (i + 1) % 10000 == 0:
             progress = (i + 1) / total_spins
             print(f"\r  ... [{int(progress * 20) * '='}>{(19 - int(progress * 20)) * ' '}] {i+1:,} ゲームプレイ済み ({time.time() - start_time:.2f}s)", end="")
        spin(state, verbose=False)
        credit_history.append(state.total_payout)
    
    print(f"\n\n--- 設定 {setting_level} シミュレーション完了 ({total_spins:,} ゲーム) ---")
    
    payout_rate = (state.total_payout + total_spins * MEDALS_PER_SPIN) / (total_spins * MEDALS_PER_SPIN)
    print(f"算出された出率: {payout_rate:.2%}")
    
    middle_cherry_prob = total_spins / state.middle_cherry_hits if state.middle_cherry_hits > 0 else 0
    print(f"中段チェリー: {state.middle_cherry_hits:,}回 (1 / {middle_cherry_prob:,.0f})")

    doki_prob = total_spins / state.doki_doki_entries if state.doki_doki_entries > 0 else 0
    print(f"ドキドキモード突入: {state.doki_doki_entries:,}回 (1 / {doki_prob:,.0f})")
    
    super_doki_prob = total_spins / state.super_doki_doki_entries if state.super_doki_doki_entries > 0 else 0
    print(f"超ドキドキモード突入: {state.super_doki_doki_entries:,}回 (1 / {super_doki_prob:,.0f})")

    # 新しい統計情報を表示
    print(f"最大連荘数: {state.max_renchan_count}回")
    print(f"最大連荘獲得枚数: {state.max_renchan_payout:,.0f}枚")
    print(f"最終持ちメダル: {state.total_payout:,.0f}枚")

    plt.clear_figure()
    plt.plot(credit_history)
    plt.title(f"設定 {setting_level} - {total_spins:,} ゲームのクレジット履歴")
    plt.xlabel("総ゲーム数")
    plt.ylabel("クレジット")
    plt.show()

if __name__ == "__main__":
    try:
        games = 10000
        setting = 1

        if len(sys.argv) > 1:
            games = int(sys.argv[1])
        if len(sys.argv) > 2:
            setting = int(sys.argv[2])

        if setting not in SETTINGS:
            raise ValueError(f"設定レベル {setting} が見つかりません。")
        if games <= 0:
            raise ValueError("ゲーム数は正の整数である必要があります。")

        run_simulation(games, setting)

    except (ValueError, IndexError) as e:
        print(f"\nエラー: 無効な引数です。 {e}")
        print("使用法: python3 terminal_graph_simulator.py [ゲーム数] [設定]")
        print("例: python3 terminal_graph_simulator.py 10000 6")
        sys.exit(1)
