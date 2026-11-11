import robocode.control.*;
import robocode.control.events.*;
import java.io.*;
/** Usage: RunBattle ROBOCODE_HOME ROUNDS SEED */
public class RunBattle {
    public static void main(String[] args) {
        System.setProperty("java.awt.headless","true");
        RandomFactory.setRandom(new java.util.Random(Long.parseLong(args[2])));
        RobocodeEngine engine=new RobocodeEngine(new File(args[0]));
        engine.setVisible(false);
        engine.addBattleListener(new BattleAdaptor() {
            public void onBattleError(BattleErrorEvent e) { System.err.println(e.getError()); }
            public void onBattleCompleted(BattleCompletedEvent e) {
                for (robocode.BattleResults r:e.getSortedResults())
                    System.out.println(r.getTeamLeaderName()+" score="+r.getScore()+" wins="+r.getFirsts());
            }
        });
        RobotSpecification[] robots=engine.getLocalRepository("lutbot.LearningTank*,sample.SpinBot");
        if (robots.length!=2) throw new IllegalStateException("Expected two robots, got "+robots.length);
        engine.runBattle(new BattleSpecification(Integer.parseInt(args[1]),
                          new BattlefieldSpecification(800,600),robots),true);
        engine.close(); System.exit(0);
    }
}
