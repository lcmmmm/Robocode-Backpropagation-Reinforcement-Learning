# CPEN 502 Part 2 測試與報告編譯步驟

以下以 Windows PowerShell 為例。ZIP 解壓後，先進入 CPEN502_Part2 資料夾。

## 1. 只編譯報告

CPEN502_Part2_Report.tex 已內嵌報告的文字、表格與程式碼附錄；五張圖仍位於 figures/，所以請保留這個資料夾。

### Overleaf

1. New Project → Upload Project，上傳本 ZIP。
2. 將 Main document 設為 CPEN502_Part2_Report.tex。
3. Compiler 選 pdfLaTeX，按 Recompile。
4. 目前版本應產生 19 頁報告。

### 本機 LaTeX

在含有 CPEN502_Part2_Report.tex 與 figures/ 的資料夾執行：

```powershell
pdflatex -interaction=nonstopmode -halt-on-error CPEN502_Part2_Report.tex
pdflatex -interaction=nonstopmode -halt-on-error CPEN502_Part2_Report.tex
```

需安裝含 geometry、amsmath、amssymb、booktabs、array、graphicx、xcolor、listings、float、hyperref、caption 的 LaTeX 環境。第二次編譯用於更新圖表編號與交叉引用。編譯不需要執行 Robocode。

## 2. 環境準備

使用 Classic Robocode 1.9.5.6 與 JDK 17，不是 Robocode Tank Royale。實驗程式需要 java 與 javac；只有 Java 執行環境而沒有編譯器時，javac 會無法執行。

```powershell
java -version
javac -version
python --version
python -m pip install numpy pandas matplotlib
$env:ROBOCODE_HOME = "C:\robocode"
Test-Path "$env:ROBOCODE_HOME\libs\robocode.jar"
```

最後一行應回傳 True。請將 C:\robocode 換成實際安裝位置。

## 3. 編譯坦克與對戰控制器

```powershell
$robotSources = Get-ChildItem .\src\lutbot\*.java | Select-Object -ExpandProperty FullName
javac -cp "$env:ROBOCODE_HOME\libs\robocode.jar" -d "$env:ROBOCODE_HOME\robots" $robotSources
New-Item -ItemType Directory -Force .\runner | Out-Null
javac -cp "$env:ROBOCODE_HOME\libs\robocode.jar" -d .\runner .\src\RunBattle.java
```

成功時通常不會輸出訊息，應產生：

- Robocode/robots/lutbot/CommonInterface.class
- Robocode/robots/lutbot/LUT.class
- Robocode/robots/lutbot/LearningTank.class
- runner/RunBattle.class 與其內部類別

RunBattle 應位於獨立 runner 資料夾。不要把整個 robots 目錄加入執行控制器的 JVM classpath，以免產生類別載入或機器人檔案權限問題。

若出現找不到 sample.SpinBot，將內建對手的原始碼重新編譯：

```powershell
javac -cp "$env:ROBOCODE_HOME\libs\robocode.jar" -d "$env:ROBOCODE_HOME\robots" "$env:ROBOCODE_HOME\robots\sample\SpinBot.java"
```

## 4. 執行 LUT 單元檢查

使用隨附的實際訓練後 LUT：

```powershell
New-Item -ItemType Directory -Force .\checks | Out-Null
javac -cp "$env:ROBOCODE_HOME\libs\robocode.jar" -d .\checks .\src\lutbot\CommonInterface.java .\src\lutbot\LUT.java .\src\LUTChecks.java
java -cp "$env:ROBOCODE_HOME\libs\robocode.jar;checks" LUTChecks .\results\q_dense_e01_seed0.lut
```

預期以 PASS 開頭，涵蓋：1,296 個索引與反解、train 的誤差回傳、TD 計算、Q-learning/SARSA target、終局更新、epsilon 選擇、隨機平手處理、讀回 Q 值與訪問次數，以及損壞檔案拒絕。

RobocodeFileOutputStream 需要 Robocode 機器人執行緒，因此獨立的 LUTChecks 讀取已由機器人保存的檔案；實際寫檔與重新載入則由接下來的對戰測試驗證。

## 5. 快速對戰測試

測試程式會寫入 results/ 和 experiment.json。為保留隨附的原始報告結果，先建立另一份程式資料夾，再跑少量回合。

假設目前位於 CPEN502_Part2：

```powershell
Copy-Item . ..\CPEN502_Part2_smoke -Recurse
Set-Location ..\CPEN502_Part2_smoke
python run_experiments.py --home "$env:ROBOCODE_HOME" --runner .\runner --seeds 1 --rounds 20 --evaluation 10 --jobs 1
```

這會執行七個條件，各 20 回合訓練與 10 回合評估，共 210 回合。預期終端機逐組顯示 train/eval 勝場，正常結束而沒有例外。

每組應有：

- results/*_seed0_train.csv：20 筆資料，不含標題列。
- results/*_seed0_eval.csv：10 筆資料，updates 欄全部為 0。
- results/*_seed0.lut：15,560 bytes。
- 對應的 train/eval .log。

程式會自動檢查回合數、結果欄位，以及評估結束後 LUT 是否與訓練後的檔案完全相同。快速測試用於確認程式可執行，不能拿來支持正式報告的學習結論；不要對只有一個 seed 的快速測試資料直接執行預設 analyze.py，因為正式分析預期五個 seeds。

## 6. 重跑完整報告實驗

另外複製一份程式資料夾作為完整重跑目錄，然後在該目錄執行：

```powershell
python run_experiments.py --home "$env:ROBOCODE_HOME" --runner .\runner --seeds 5 --rounds 800 --evaluation 200 --jobs 3
python run_baseline.py --home "$env:ROBOCODE_HOME" --runner .\runner
python analyze.py
python make_report_stats.py
pdflatex -interaction=nonstopmode -halt-on-error report.tex
pdflatex -interaction=nonstopmode -halt-on-error report.tex
```

若電腦資源不足，可將 --jobs 3 改為 --jobs 1；這只改變同時執行的實驗數量。

正式實驗包含七個條件 × 五個 seeds × (800 訓練 + 200 評估) = 35,000 回合；run_baseline.py 再執行五組各 200 回合的未訓練參考對戰，合計 36,000 回合。

完成後應有：

- 35 份訓練 CSV 與 40 份評估 CSV。
- 35 份訓練後二進位 LUT。
- summary.csv、summary.json。
- figures/ 的五張圖，各含 PDF 與 PNG。
- trained_lut/ 的五份基準條件完整 LUT CSV。
- 更新後的 report.pdf。

注意：完整重跑後請編譯 report.tex。它會讀入 make_report_stats.py 更新的表格及討論。CPEN502_Part2_Report.tex 是原報告的整合快照，方便獨立編輯與交付；它不會自動讀入重跑後的新數字。

不同 JVM、Robocode 版本、CPU 排程及 skipped turns 可能讓重跑勝率不同，不能要求每次都逐位數相同；請以你重跑產生的 CSV 為準。

## 7. 在 Robocode GUI 觀察已訓練策略

完成 Java 編譯後，於原始套件目錄執行：

```powershell
$dataDir = Join-Path $env:ROBOCODE_HOME "robots\lutbot\LearningTank.data"
New-Item -ItemType Directory -Force $dataDir | Out-Null
Copy-Item .\results\q_dense_e01_seed0.lut (Join-Path $dataDir "trained.lut")
@'
seed=10000
epsilon=0
algorithm=q
intermediate=true
learning=false
resume=true
'@ | Set-Content -Encoding ascii (Join-Path $dataDir "config.properties")
```

開啟 Robocode → Battle → New，選 lutbot.LearningTank 與 sample.SpinBot，戰場設為 800 × 600。選擇例如 20 回合後開始。

這個設定載入 LUT、關閉探索並停止學習，用來觀察已訓練策略。若要從零開始訓練，改為 learning=true、resume=false、epsilon=0.1。LUT 會在最後一回合寫入 trained.lut，metrics.csv 記錄各回合表現，第一回合會重設舊紀錄。

## 常見問題

- javac 找不到：確認安裝 JDK 17 並將其 bin 加入 PATH。
- Expected two robots 或找不到 SpinBot：確認 .class 位置，並重新編譯 sample/SpinBot.java。
- ThreadManager cannot be null：不要在獨立程式直接呼叫 LUT.save；寫檔需在 Robocode 內執行。
- Missing figures/*.pdf：請使用完整 ZIP，保留 figures/，並在報告主檔所在資料夾編譯。
- Java 17 出現 SecurityManager deprecated 警告：這是本次舊版 Robocode 執行時可見的警告，請另外確認是否有 Exception 或實際測試失敗。
