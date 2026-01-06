

`plotext`をインストールするには、ターミナルで以下のコマンドのいずれかを実行してください。

最も一般的なインストール方法:
```bash
pip install plotext
```

もし上記のコマンドがうまくいかない場合（例: `pip: command not found` のようなエラーが出る場合）、`python` または `python3` コマンドを使ってモジュールとして`pip`を実行してみてください:
```bash
python -m pip install plotext
# または
python3 -m pip install plotext
```

それでも問題が解決しない場合は、お使いのシステムで `pip` が正しくインストールされているか、またはPATHが設定されているか確認する必要があるかもしれません。

インストールが完了したら、新しく作成した `terminal_graph_simulator.py` スクリプトを実行できます。

**実行方法の例:**
設定6で1000ゲームのシミュレーションとグラフを表示する場合:
```bash
python3 terminal_graph_simulator.py 1000 6
```
(ゲーム数と設定は任意で変更してください。)
