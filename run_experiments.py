"""Run real Robocode battles. No synthetic result generation.
Requires Java 17 and a classic Robocode 1.9.5.6 installation.
Compile src first (README). Run: python run_experiments.py --home PATH
"""
import argparse, concurrent.futures, csv, json, pathlib, shutil, subprocess, time
ROOT = pathlib.Path(__file__).resolve().parent
CONDITIONS = [("q_dense_e0", "q", True, 0.0),
              ("q_dense_e01", "q", True, 0.1),
              ("q_dense_e03", "q", True, 0.3),
              ("q_dense_e06", "q", True, 0.6),
              ("q_dense_e1", "q", True, 1.0),
              ("sarsa_dense_e01", "sarsa", True, 0.1),
              ("q_terminal_e01", "q", False, 0.1)]
JAVA_FLAGS = ["-Xmx384m", "-Djava.security.manager=allow",
              "-Dsun.reflect.noInflation=true",
              "--add-opens=java.base/java.lang=ALL-UNNAMED",
              "--add-opens=java.base/java.lang.reflect=ALL-UNNAMED",
              "--add-opens=java.base/sun.net.www.protocol.jar=ALL-UNNAMED"]
def one_seed(seed, args):
    home = (ROOT / "work" / f"seed{seed}").resolve()
    if home.exists(): shutil.rmtree(home)
    shutil.copytree(args.home, home)
    data = home / "robots/lutbot/LearningTank.data"
    data.mkdir(parents=True, exist_ok=True)
    outdir = ROOT / "results"
    outdir.mkdir(exist_ok=True)
    for name, algorithm, dense, epsilon in CONDITIONS:
        (home/'robots/robot.database').unlink(missing_ok=True)
        prefix = outdir / f"{name}_seed{seed}"
        for phase, rounds in [("train",args.rounds),("eval",args.evaluation)]:
            for f in ["metrics.csv", "config.properties"]:
                (data/f).unlink(missing_ok=True)
            if phase=="train": (data/"trained.lut").unlink(missing_ok=True)
            config = dict(seed=seed if phase=="train" else 10000+seed,
                          epsilon=epsilon if phase=="train" else 0,
                          algorithm=algorithm, intermediate=str(dense).lower(),
                          learning=str(phase=="train").lower(),
                          resume=str(phase=="eval").lower())
            (data/"config.properties").write_text("".join(f"{k}={v}\n" for k,v in config.items()))
            runner = pathlib.Path(args.runner).resolve()
            import os
            cp = str(home/"libs/robocode.jar") + os.pathsep + str(runner)
            cmd = ["java"]+JAVA_FLAGS+["-cp",cp,"RunBattle",str(home),str(rounds),
                                      str(config["seed"])]
            t=time.time()
            with open(str(prefix)+f"_{phase}.log","w") as log:
                subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1800,cwd=home)
            rows=list(csv.DictReader((data/"metrics.csv").open()))
            if len(rows)!=rounds or any(r['outcome'] not in ('0','1') for r in rows):
                raise RuntimeError(f"Incomplete battle: {name} seed {seed}")
            logtext=pathlib.Path(str(prefix)+f"_{phase}.log").read_text()
            if any(x in logtext for x in ('Exception','Preventing','SYSTEM:')):
                raise RuntimeError(f"Engine/robot failure: {prefix}_{phase}.log")
            shutil.copy2(data/"metrics.csv",str(prefix)+f"_{phase}.csv")
            if phase=="train": shutil.copy2(data/"trained.lut",str(prefix)+".lut")
            else:
                if (data/"trained.lut").read_bytes()!=pathlib.Path(str(prefix)+".lut").read_bytes():
                    raise RuntimeError("Evaluation changed LUT")
            wins=sum(int(r['outcome']) for r in rows)
            print(f"{name} seed={seed} {phase}: {wins}/{rounds} ({time.time()-t:.1f}s)",flush=True)
    return seed
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument('--home',type=pathlib.Path,required=True)
    p.add_argument('--runner',default=str(ROOT/'runner'))
    p.add_argument('--rounds',type=int,default=800)
    p.add_argument('--evaluation',type=int,default=200)
    p.add_argument('--seeds',type=int,default=5)
    p.add_argument('--jobs',type=int,default=3)
    args=p.parse_args(); args.home=args.home.resolve()
    (ROOT/'experiment.json').write_text(json.dumps(dict(engine='Robocode 1.9.5.6',
       opponent='sample.SpinBot',battlefield=[800,600],train_rounds=args.rounds,
       evaluation_rounds=args.evaluation,seeds=list(range(args.seeds)),
       evaluation_seeds=[10000+i for i in range(args.seeds)],conditions=CONDITIONS,
       alpha=0.1,gamma=0.95,action_ticks=16),indent=2))
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        list(pool.map(lambda s:one_seed(s,args),range(args.seeds)))
