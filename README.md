# Oki Doki DUO Encore Simulation - Version 2

This is a highly accurate simulation of the "スマスロ沖ドキDUOアンコール" pachislot machine, aiming to replicate the real machine's payout rate.

## How to Run

### Interactive Mode
```bash
# Setting 1 (Default)
python3 simulation_runner.py

# Setting 6
python3 simulation_runner.py 6
```

### Simulation Mode (for payout rate verification)
```bash
# Setting 1 (Default)
python3 simulation_runner.py --simulate 1000000

# Setting 6
python3 simulation_runner.py --simulate 1000000 6
```

## Key Improvements in V2
- **Accurate Payout Rate:** Includes small wins (Koyaku) and more realistic probabilities to closely match the official payout rates.
- **Detailed Game Modes:** Simulates `Normal A`, `Normal B`, and `Chance` modes.
- **Realistic Probabilities:** Incorporates researched data for small wins, mode transitions, and bonus probabilities.
- **Verification Feature:** A simulation mode to run millions of games and verify the payout rate.
- **Web UI:** A graphical user interface to play the game interactively in a browser.

---

## Web UIの機能

`python3 server.py [設定]` を実行して表示されるWeb UIには、以下の機能が含まれています。

### 1. メイン画面
*   **ゲームパネル:** 現在のモード、クレジット、ボーナスからのゲーム数、総ゲーム数が表示されます。
*   **ハイビスカスランプ:** ボーナスに当選すると、ハイビスカスランプが鮮やかに点灯します。

### 2. 操作
*   **SPINボタン:** 1ゲームずつプレイします。
*   **SKIPボタン:** 次のボーナスに当選するまで、ゲームを高速で自動的に消化（スキップ）します。
*   **Enterキー:** `SPIN`ボタンのショートカットとして機能します。

### 3. データ可視化
*   **クレジット推移グラフ (Credit History):**
    *   ゲームの進行に応じて、クレジットがどのように増減したかを折れ線グラフで表示します。
    *   横軸が総ゲーム数、縦軸がクレジット数です。
*   **ボーナス履歴 (Bonus History):**
    *   当選した全てのボーナスが一覧で記録されます。
    *   以下の情報が一行ごとに表示されます。
        *   ボーナス種別 (BIG / REG)
        *   当選時の総ゲーム数
        *   **前回ボーナスからのゲーム数**
        *   当選後のモード

---

## シミュレーション仕様詳細 (Version 2.1)

現在のシミュレーションにおける内部的な確率および仕様の一覧です。

### 設定ごとの確率

| 項目 | 設定1 | 設定2 | 設定3 | 設定5 | 設定6 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ボーナス初当たり** | 1/240.0 | 1/230.2 | 1/215.8 | 1/192.1 | 1/181.0 |
| **チェリー** | 1/46.8 | 1/45.0 | 1/43.3 | 1/41.7 | 1/40.3 |

### 全設定共通の確率

*   **ベル:** `1 / 8.2`
*   **リプレイ:** `1 / 7.2`
*   **スイカ:** `1 / 143.7`
*   **確定役:** `1 / 4369.1`
*   **BIG/REG比率:** BIG `70%` / REG `30%` (推定値)

### モード移行確率 (ボーナス当選時・推定値)

*   **通常A滞在中:**
    *   `53%` → 通常A (ループ)
    *   `15%` → 通常Bへ移行
    *   `32%` → 天国へ移行
*   **通常B滞在中:**
    *   `50%` → 通常B (ループ)
    *   `50%` → 天国へ移行
*   **チャンス滞在中:**
    *   `40%` → 通常Aへ転落
    *   `60%` → 天国へ移行
*   **天国滞在中:**
    *   `75%` → 天国 (ループ)
    *   `5%` → ドキドキへ移行
    *   `10%` → 通常Aへ転落
    *   `10%` → 通常Bへ転落
*   **ドキドキ滞在中:**
    *   `80%` → ドキドキ (ループ)
    *   `2%` → 超ドキドキへ移行
    *   `9%` → 通常Aへ転落
    *   `9%` → 通常Bへ転落

### 天国モードの仕様

*   ボーナス後、32ゲーム間滞在します。
*   滞在中は、ゲーム数ごとに重み付けされた特別な確率テーブルに基づき、毎ゲーム高確率でボーナスを抽選します。
*   32ゲーム以内にボーナスに当選しなかった場合、**通常Aモードに転落**します。

### 天井の仕様

*   **ゲーム数天井:** ボーナス間 `800` ゲーム消化でボーナスに当選します。
*   **スルー回数天井:** 天国モードに移行しないボーナスが `10` 回連続すると、次回のボーナスで天国モードへの移行が優遇されます（※シミュレーションでは強制的にボーナス当選としています）。
