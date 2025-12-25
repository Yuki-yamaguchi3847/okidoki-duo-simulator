import random
import time
import sys
from collections import defaultdict

# --- ゲーム定数 (Version 2.1) ---

# 払い出し枚数に関する定数
MEDALS_PER_SPIN = 3  # 1ゲームあたりの投入メダル数
BONUS_PAYOUT = {"BIG": 204, "REG": 84}  # 各ボーナスでの払い出し枚数

# 小役の確率と払い出し枚数 (出率調整版)
KOYAKU = {
    "REPLAY":       {"prob": 1 / 7.2, "payout": MEDALS_PER_SPIN},  # リプレイの確率と払い出し（投入分が返ってくる）
    "BELL":         {"prob": 1 / 8.2, "payout": 10},  # ベルの確率と払い出し
    "WATERMELON":   {"prob": 1 / 143.7, "payout": 5},  # スイカの確率と払い出し
    "CHERRY":       {"prob": 1 / 46.8, "payout": 3},  # チェリーの確率と払い出し（設定1の値。GameStateで上書き）
    "GUARANTEED":   {"prob": 1 / 4369.1, "payout": 0},  # 確定役の確率。払い出しは強制当選するボーナスで行う
}

# 台の設定ごとの情報
SETTINGS = {
    1: {"bonus_prob": 1 / 240.0, "cherry_prob": 1 / 46.8, "name": "Setting 1", "payout_rate": 0.972},
    2: {"bonus_prob": 1 / 230.2, "cherry_prob": 1 / 45.0, "name": "Setting 2", "payout_rate": 0.986},
    3: {"bonus_prob": 1 / 215.8, "cherry_prob": 1 / 43.3, "name": "Setting 3", "payout_rate": 1.024},
    4: {"bonus_prob": 1 / 192.1, "cherry_prob": 1 / 41.7, "name": "Setting 5", "payout_rate": 1.068}, # 設定4は存在しない
    5: {"bonus_prob": 1 / 192.1, "cherry_prob": 1 / 41.7, "name": "Setting 5", "payout_rate": 1.068},
    6: {"bonus_prob": 1 / 181.0, "cherry_prob": 1 / 40.3, "name": "Setting 6", "payout_rate": 1.10},
}

# ゲームモードの定義
MODE_NORMAL_A = "Normal A"
MODE_NORMAL_B = "Normal B"
MODE_CHANCE = "Chance"
MODE_TENGOKU = "Tengoku"
MODE_DOKI_DOKI = "Doki Doki"
MODE_SUPER_DOKI_DOKI = "Super Doki Doki"
MODE_DUO = "DUO"

# 天井のゲーム数
GAME_CEILING = 800  # ボーナス間天井
THROUGH_CEILING = 10  # スルー回数天井

# 天国モード（32G）中のゲーム数ごとのボーナス当選確率のテーブル
TENGOKU_PROB_TABLE = [0.15] * 5 + [0.05] * 5 + [0.02] * 10 + [0.05] * 5 + [0.15] * 7
TENGOKU_PROB_TABLE = [p / sum(TENGOKU_PROB_TABLE) * 1.1 for p in TENGOKU_PROB_TABLE]

# ボーナス当選後のモード移行確率（推定値・出率調整版）
MODE_TRANSITIONS = {
    MODE_NORMAL_A: {MODE_NORMAL_A: 0.53, MODE_NORMAL_B: 0.15, MODE_TENGOKU: 0.32},
    MODE_NORMAL_B: {MODE_NORMAL_B: 0.50, MODE_TENGOKU: 0.50},
    MODE_CHANCE:   {MODE_NORMAL_A: 0.40, MODE_TENGOKU: 0.60},
    MODE_TENGOKU:  {MODE_TENGOKU: 0.75, MODE_DOKI_DOKI: 0.05, MODE_NORMAL_A: 0.10, MODE_NORMAL_B: 0.10},
    MODE_DOKI_DOKI:{MODE_DOKI_DOKI: 0.80, MODE_SUPER_DOKI_DOKI: 0.02, MODE_NORMAL_A: 0.09, MODE_NORMAL_B: 0.09},
    MODE_DUO:      {MODE_DUO: 0.80, MODE_NORMAL_A: 0.20}, # 簡易的な実装
}

# --- クラス定義 ---
class Player:
    """プレイヤーの状態を管理するクラス（インタラクティブモード用）"""
    def __init__(self, initial_credits=1000):
        self.credits = initial_credits

class GameState:
    """シミュレーション全体のゲーム状態を管理するクラス"""
    def __init__(self, setting_level=1, is_reset=True):
        self.setting = SETTINGS[setting_level]
        KOYAKU["CHERRY"]["prob"] = self.setting["cherry_prob"]
        
        self.total_games = 0
        self.total_payout = 0
        self.games_since_bonus = 0
        self.bonus_count = defaultdict(int)
        self.koyaku_counts = defaultdict(int)
        self.bonus_through_count = 0
        
        if is_reset:
            rand = random.random()
            if rand < 0.50: self.current_mode = MODE_NORMAL_A
            elif rand < 0.602: self.current_mode = MODE_NORMAL_B
            else: self.current_mode = MODE_CHANCE
        else:
            self.current_mode = MODE_NORMAL_A

    def is_tengoku(self):
        """現在が天国系モードかどうかを判定する"""
        return self.current_mode in [MODE_TENGOKU, MODE_DOKI_DOKI, MODE_SUPER_DOKI_DOKI]

    def get_payout_rate(self):
        """現在の出率（機械割）を計算して返す"""
        if self.total_games == 0: return 0.0
        return self.total_payout / (self.total_games * MEDALS_PER_SPIN)

# --- コア関数 ---
def get_mode_transition(current_mode):
    """ボーナス当選時の次のモードを確率に応じて決定する"""
    transitions = MODE_TRANSITIONS.get(current_mode, {MODE_NORMAL_A: 1.0})
    rand = random.random()
    cumulative_prob = 0
    for mode, prob in transitions.items():
        cumulative_prob += prob
        if rand < cumulative_prob:
            return mode
    return list(transitions.keys())[-1]

def play_bonus(state, bonus_type, verbose=True):
    """ボーナス当選時の処理を行う"""
    payout = BONUS_PAYOUT[bonus_type]
    state.total_payout += payout
    if verbose: print(f"🎉 {bonus_type} BONUS! Payout: {payout} 🎉")
    
    state.bonus_count[bonus_type] += 1
    state.games_since_bonus = 0

    new_mode = get_mode_transition(state.current_mode)
    if new_mode != state.current_mode:
        if verbose: print(f"Mode changed: {state.current_mode} -> {new_mode}")
        state.current_mode = new_mode
    
    if state.is_tengoku():
        state.bonus_through_count = 0
    else:
        state.bonus_through_count += 1

def spin(state, verbose=True):
    """1ゲームの抽選処理を行う"""
    state.total_games += 1
    state.games_since_bonus += 1

    # 天国モード32G消化時のモード転落チェック
    if state.is_tengoku() and state.games_since_bonus > 32:
        if verbose: print("Tengoku mode finished after 32 games.")
        state.current_mode = MODE_NORMAL_A # Aに転落
        state.bonus_through_count = 1 # スルー回数を1に

    payout = 0
    bonus_hit = False
    
    # 1. 天井判定
    if state.games_since_bonus >= GAME_CEILING or state.bonus_through_count >= THROUGH_CEILING:
        if verbose: print("Ceiling reached! Guaranteed bonus!")
        bonus_hit = True

    # 2. 天国モード中のボーナス判定
    if not bonus_hit and state.is_tengoku() and state.games_since_bonus <= 32:
        if random.random() < TENGOKU_PROB_TABLE[state.games_since_bonus - 1]:
            bonus_hit = True

    # 3. 確定役の判定
    if not bonus_hit and random.random() < KOYAKU["GUARANTEED"]["prob"]:
        if verbose: print("Guaranteed Win Hit!")
        state.koyaku_counts["GUARANTEED"] += 1
        bonus_hit = True

    # 4. 通常のボーナス判定
    if not bonus_hit and random.random() < state.setting["bonus_prob"]:
         bonus_hit = True
    
    # 5. 小役の判定（ボーナス非当選時のみ）
    if not bonus_hit:
        rand = random.random()
        cumulative_prob = 0
        for name, data in KOYAKU.items():
            if name == "GUARANTEED": continue
            cumulative_prob += data["prob"]
            if rand < cumulative_prob:
                payout += data["payout"]
                state.koyaku_counts[name] += 1
                break
    
    state.total_payout += payout

    if bonus_hit:
        bonus_type = "BIG" if random.random() < 0.7 else "REG"
        play_bonus(state, bonus_type, verbose)
        
    return payout

def run_simulation(total_spins, setting_level):
    """指定されたゲーム数だけシミュレーションを自動実行し、統計情報を表示する"""
    print(f"--- Running simulation for {total_spins:,} games on {SETTINGS[setting_level]['name']} ---")
    state = GameState(setting_level=setting_level)
    
    start_time = time.time()
    for i in range(total_spins):
        if (i + 1) % 100000 == 0:
            elapsed = time.time() - start_time
            print(f"  ... {i+1:,} games played ({elapsed:.2f}s, Payout: {state.get_payout_rate():.4f}) ...")
        spin(state, verbose=False)

    print("\n--- Simulation Complete ---")
    print(f"Total Games: {state.total_games:,}")
    print(f"Total Invested: {state.total_games * MEDALS_PER_SPIN:,} medals")
    print(f"Total Payout: {state.total_payout:,.0f} medals")
    
    calculated_rate = state.get_payout_rate()
    target_rate = SETTINGS[setting_level]['payout_rate']
    print(f"\nCalculated Payout Rate: {calculated_rate:.4f} ({calculated_rate:.2%})")
    print(f"Target Payout Rate:     {target_rate:.4f} ({target_rate:.2%})")
    print("-" * 20)
    print("Bonus Counts:", dict(state.bonus_count))
    print("Koyaku Counts:", dict(state.koyaku_counts))

def main_interactive(setting_level=1):
    """対話形式で1ゲームずつプレイするための関数（デバッグ用）"""
    player = Player()
    state = GameState(setting_level=setting_level)
    print("--- Welcome to Oki Doki DUO Encore (V2)! ---")
    print(f"Starting with {player.credits} credits on {state.setting['name']}.")

    try:
        while player.credits >= MEDALS_PER_SPIN:
            action = input(f"[{state.current_mode}] Cr: {player.credits} | G: {state.games_since_bonus} | Enter to spin: ")
            if action.lower() == 'q': break
            
            player.credits -= MEDALS_PER_SPIN
            payout = spin(state, verbose=True)
            player.credits += payout

            if payout > 0 and not state.bonus_count:
                 print(f"  > Koyaku hit! Payout: {payout}")

    except KeyboardInterrupt:
        print("\nStopping game...")
    
    print("\n--- Game Over ---")
    print(f"Final Credits: {player.credits}")
    print(f"Payout Rate: {state.get_payout_rate():.4f}")

# --- メイン処理 ---
if __name__ == "__main__":
    interactive_setting = 1 # デフォルト設定
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--simulate':
            try:
                # 第2引数でゲーム数、第3引数で設定を指定
                total_spins = int(sys.argv[2]) if len(sys.argv) > 2 else 1_000_000
                setting = int(sys.argv[3]) if len(sys.argv) > 3 else 1
                if setting not in SETTINGS:
                    print(f"Error: Setting level {setting} not found.")
                else:
                    # シミュレーションモードを実行
                    run_simulation(total_spins, setting)
            except (ValueError, IndexError):
                print("Usage: python simulation_runner.py --simulate [number_of_games] [setting_level]")
            sys.exit(0)
        else:
            # --simulate フラグがない場合、最初の引数を設定レベルとして解釈
            try:
                potential_setting = int(sys.argv[1])
                if potential_setting in SETTINGS:
                    interactive_setting = potential_setting
                else:
                    print(f"Warning: Setting level {potential_setting} not found. Defaulting to Setting 1.")
            except ValueError:
                print(f"Warning: Invalid argument '{sys.argv[1]}'. Defaulting to Setting 1.")
    
    # 引数がない場合、または --simulate 以外の場合は対話モードを実行
    main_interactive(interactive_setting)
