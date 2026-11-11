"""Evaluate an untrained zero LUT under the same held-out seeds."""
from pathlib import Path
import argparse, csv, os, shutil, subprocess
from run_experiments import ROOT, JAVA_FLAGS
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--home',type=Path,required=True)
    p.add_argument('--runner',type=Path,default=ROOT/'runner'); args=p.parse_args()
    home=ROOT/'work'/'untrained';
    if home.exists(): shutil.rmtree(home)
    shutil.copytree(args.home.resolve(),home)
    (home/'robots/robot.database').unlink(missing_ok=True)
    data=home/'robots/lutbot/LearningTank.data'
    for seed in range(5):
        (data/'config.properties').write_text(f'seed={10000+seed}\nepsilon=0\nalgorithm=q\nintermediate=true\nlearning=false\nresume=false\n')
        cmd=['java']+JAVA_FLAGS+['-cp',str(home/'libs/robocode.jar')+os.pathsep+str(args.runner.resolve()),
                                  'RunBattle',str(home),'200',str(10000+seed)]
        with (ROOT/'results'/f'untrained_seed{seed}_eval.log').open('w') as log:
            subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True,cwd=home)
        rows=list(csv.DictReader((data/'metrics.csv').open()))
        assert len(rows)==200 and all(int(r['coverage'])==0 for r in rows)
        shutil.copy2(data/'metrics.csv',ROOT/'results'/f'untrained_seed{seed}_eval.csv')
        print(seed,sum(int(r['outcome']) for r in rows),flush=True)
