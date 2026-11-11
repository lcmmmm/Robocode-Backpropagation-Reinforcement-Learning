# CPEN 502 Part 2 — Robocode LUT reinforcement learning

This package contains real Robocode experiment data, a submission report, Java
source, plotting code, and trained look-up tables. It does not contain a substitute
simulator. The opponent is the unmodified classic Robocode sample.SpinBot.

## Requirements

- Classic Robocode 1.9.5.6 (not Tank Royale), Java 17 JDK (`java` and `javac`).
- Python 3 with numpy, pandas, matplotlib for analysis.
- LaTeX with amsmath, booktabs, listings, graphicx, geometry for report rebuilding.

## Build and run

Set ROBOCODE_HOME to your installed Robocode directory. From this directory:

```bash
javac -cp "$ROBOCODE_HOME/libs/robocode.jar" -d "$ROBOCODE_HOME/robots" src/lutbot/*.java
# Keep the controller OUTSIDE robots and do not put robots on the JVM classpath.
mkdir -p runner
javac -cp "$ROBOCODE_HOME/libs/robocode.jar" -d runner src/RunBattle.java
python run_experiments.py --home "$ROBOCODE_HOME" --runner runner --seeds 5 --rounds 800 --evaluation 200 --jobs 3
python run_baseline.py --home "$ROBOCODE_HOME" --runner runner
python analyze.py
python make_report_stats.py
pdflatex -interaction=nonstopmode report.tex
pdflatex -interaction=nonstopmode report.tex
```

The supplied experiment driver uses `java` on PATH and sets Java 17 runtime flags.
On Windows use PowerShell equivalents for compilation and environment variables;
the Python driver constructs the classpath with the correct platform separator.
A Java 17-compatible Eclipse compiler (ECJ 3.37.0) was used for the recorded runs.
The preinstalled SpinBot source was recompiled without modification for Java 17.
If your installation does not discover SpinBot, compile its source as well:

```bash
javac -cp "$ROBOCODE_HOME/libs/robocode.jar" -d "$ROBOCODE_HOME/robots" "$ROBOCODE_HOME/robots/sample/SpinBot.java"
```

Each seed has an isolated engine installation under work/; conditions run
sequentially within that installation. All conditions start with a fresh zero LUT.
Training and evaluation each run in a fresh JVM. The controller seeds Robocode's
RandomFactory; the robot independently seeds epsilon-greedy action selection.
Evaluation loads the trained table, sets epsilon=0 and disables learning; the
runner verifies the resulting LUT is byte-identical. Exact outcomes may vary with
JVM/Robocode version, CPU scheduling and skipped turns.

## Files

- src/lutbot/: Java common interface, LUT and AdvancedRobot implementation.
- src/RunBattle.java: headless engine controller.
- src/LUTChecks.java: deterministic arithmetic, policy, indexing and file checks.
- results/: 35 training logs, 40 evaluation logs and 35 trained binary LUTs.
- trained_lut/: all 1,296 rows of each of the five baseline trained LUTs as CSV.
- summary.csv and summary.json: aggregates calculated from the measured logs.
- experiment.json: exact experiment configuration and seeds.
- figures/: graph PNGs and vector PDFs.
- report.tex: editable report, including the source-code appendix.

The binary format is big endian: magic 0x4c555432, entry count 1296 (two int32s),
then 1296 pairs of float64 Q value and int32 visit count, 15,560 bytes in total.
Use LUT.load() to restore a binary file; CSV exports are for inspection and later
neural-network training. No evaluation data is used to change the trained tables.

## Use a trained robot in the GUI

Compile src/lutbot into Robocode/robots, put a trained .lut file in
robots/lutbot/LearningTank.data/trained.lut and create config.properties there:

```properties
seed=10000
epsilon=0
algorithm=q
intermediate=true
learning=false
resume=true
```

Choose lutbot.LearningTank versus sample.SpinBot in an 800 x 600 battle. To train
from scratch, set learning=true, resume=false, epsilon=0.1. The table is saved on
the last round, and metrics.csv appends one record per completed round. The first completed round truncates metrics.csv before logging the new battle. Never mix log records across runs.

## Validation

Compile src/LUTChecks.java with src/lutbot/CommonInterface.java and LUT.java into
an independent checks/ directory. Run with robocode.jar and checks/ on classpath,
passing results/q_dense_e01_seed0.lut as the sole argument. Persistence checks
read actual tables saved from within Robocode (RobocodeFileOutputStream requires
a robot thread and cannot be called by a standalone test process).

The LUT preserves Part 1's load/save/train/output_for method names. Java types
replace Python signatures. train(x,target) returns the pre-update half squared
error and installs the requested value; the RL controller applies alpha before
calling train. For a neural replacement, use the Bellman target with the neural
training method, avoiding a second unintended alpha blend. A neural network also
requires a suitable state-action input size and unrestricted Q output: the old
2-input XOR network and bounded sigmoid output cannot be reused unchanged.
