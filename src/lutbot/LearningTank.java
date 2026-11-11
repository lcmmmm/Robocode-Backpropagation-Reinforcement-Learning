package lutbot;
import robocode.*;
import robocode.util.Utils;
import java.io.*;
import java.util.*;

/** Six 16-tick macro-actions; only one opponent is supported. */
public class LearningTank extends AdvancedRobot {
    private static LUT lut;
    private static Random rng;
    private static Properties config;
    private double epsilon;
    private boolean sarsa, intermediate, learning;
    private int state=-1, action, steps, wallHits, shots, hits;
    private long nextDecision;
    private double pending, totalReward, tdAbs, dealt, received;
    private double enemyX, enemyY, enemyEnergy=100, distance=500;
    private long lastScan=-100;
    private boolean finished;
    private static String cfg(String k, String fallback) {
        return config.getProperty(k,fallback);
    }
    public void run() {
        if (getRoundNum()==0 || lut==null) {
            config = new Properties();
            try (InputStream in=new FileInputStream(getDataFile("config.properties"))) {
                config.load(in);
            } catch (IOException e) { out.println("Using default config: "+e); }
            lut = new LUT();
            rng = new Random(Long.parseLong(cfg("seed","0")));
            if (Boolean.parseBoolean(cfg("resume","false"))) {
                try { lut.load(getDataFile("trained.lut").getPath()); }
                catch(IOException e) { throw new IllegalStateException("Cannot resume",e); }
            }
        }
        if (getRoundNum()==0) out.println("CONFIG "+config);
        epsilon=Double.parseDouble(cfg("epsilon","0.1"));
        sarsa=cfg("algorithm","q").equals("sarsa");
        intermediate=Boolean.parseBoolean(cfg("intermediate","true"));
        learning=Boolean.parseBoolean(cfg("learning","true"));
        setAdjustGunForRobotTurn(true);
        setAdjustRadarForGunTurn(true);
        setAdjustRadarForRobotTurn(true);
        setTurnRadarRight(Double.POSITIVE_INFINITY);
        while (true) {
            if (lastScan>=0) {
                if (state<0 || getTime()>=nextDecision) decide();
                aimAndFire();
            }
            if (getTime()-lastScan>4)
                setTurnRadarRight(Double.POSITIVE_INFINITY);
            execute();
        }
    }
    private int energyBin(double e) { return e<30 ? 0 : e<70 ? 1 : 2; }
    private int observe() {
        double d=Math.hypot(enemyX-getX(),enemyY-getY());
        int db=d<200 ? 0 : d<400 ? 1 : 2;
        double absolute=Math.atan2(enemyX-getX(),enemyY-getY());
        double b=Utils.normalAbsoluteAngle(absolute-getHeadingRadians()+Math.PI/4);
        int bearing=(int)(b/(Math.PI/2));
        double wall=Math.min(Math.min(getX(),getBattleFieldWidth()-getX()),
                             Math.min(getY(),getBattleFieldHeight()-getY()));
        double[] x={energyBin(getEnergy()),energyBin(enemyEnergy),db,bearing,wall<80?1:0,0};
        return LUT.index(x)/LUT.ACTIONS;
    }
    private void decide() {
        int nextState=observe();
        int nextAction=lut.choose(nextState,epsilon,rng);
        if (state>=0) {
            double boot=sarsa ? lut.value(nextState,nextAction) : lut.max(nextState);
            update(pending+0.95*boot);
        }
        state=nextState; action=nextAction; pending=0;
        nextDecision=getTime()+16;
        // Reset old commands before issuing the selected macro-action.
        setAhead(0); setTurnRight(0);
        if (action==0) setAhead(120);
        if (action==1) setBack(120);
        if (action==2) { setAhead(120); setTurnLeft(45); }
        if (action==3) { setAhead(120); setTurnRight(45); }
        // Actions 4/5 stop and use a different bullet power.
    }
    private void update(double target) {
        if (!learning) return;
        tdAbs+=Math.abs(lut.update(state,action,target,0.1)); steps++;
    }
    private void aimAndFire() {
        double aim=Math.atan2(enemyX-getX(),enemyY-getY());
        setTurnGunRightRadians(Utils.normalRelativeAngle(aim-getGunHeadingRadians()));
        if (state>=0 && getTime()-lastScan<=4 && getGunHeat()==0
                && Math.abs(Utils.normalRelativeAngle(aim-getGunHeadingRadians()))<0.12) {
            double power=action==4 ? 1 : action==5 ? 3 : 2;
            if (getEnergy()>power+0.1 && setFireBullet(power)!=null) shots++;
        }
    }
    public void onScannedRobot(ScannedRobotEvent e) {
        double abs=getHeadingRadians()+e.getBearingRadians();
        distance=e.getDistance();
        enemyX=getX()+Math.sin(abs)*distance;
        enemyY=getY()+Math.cos(abs)*distance;
        enemyEnergy=e.getEnergy(); lastScan=getTime();
        double turn=Utils.normalRelativeAngle(abs-getRadarHeadingRadians());
        setTurnRadarRightRadians(turn==0 ? 0.02 : 2*turn);
    }
    private void reward(double r) {
        if (state>=0 && !finished) { pending+=r; totalReward+=r; }
    }
    public void onBulletHit(BulletHitEvent e) {
        double p=e.getBullet().getPower(), damage=4*p+Math.max(0,2*(p-1));
        dealt+=damage; hits++;
        if (intermediate) reward(damage/10.0);
    }
    public void onHitByBullet(HitByBulletEvent e) {
        double p=e.getBullet().getPower(), damage=4*p+Math.max(0,2*(p-1));
        received+=damage;
        if (intermediate) reward(-damage/10.0);
    }
    public void onHitWall(HitWallEvent e) {
        wallHits++; if (intermediate) reward(-0.2);
    }
    public void onWin(WinEvent e) { finish(1); }
    public void onDeath(DeathEvent e) { finish(0); }
    private void finish(int outcome) {
        if (finished) return;
        reward(outcome==1 ? 10 : outcome==0 ? -10 : 0);
        if (state>=0) update(pending); // Terminal target has NO bootstrap.
        finished=true;
        try {
            if (getRoundNum()==getNumRounds()-1)
                lut.save(getDataFile("trained.lut").getPath());
            try (PrintStream out=new PrintStream(new RobocodeFileOutputStream(
                        getDataFile("metrics.csv").getPath(),getRoundNum()!=0))) {
                if (getRoundNum()==0) out.println("round,outcome,reward,mean_abs_td,updates,coverage,shots,hits,dealt,received,wall_hits,ticks");
                out.printf(Locale.US,"%d,%d,%.6f,%.6f,%d,%d,%d,%d,%.3f,%.3f,%d,%d%n",
                    getRoundNum()+1,outcome,totalReward,steps==0?0:tdAbs/steps,
                    steps,lut.covered(),shots,hits,dealt,received,wallHits,getTime());
            }
        } catch(IOException e) { throw new IllegalStateException("Persistence failed",e); }
    }
}
