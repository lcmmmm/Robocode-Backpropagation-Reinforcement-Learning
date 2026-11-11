package lutbot;
import java.io.*;
import java.util.Random;
import robocode.RobocodeFileOutputStream;
/** Input: five quantized state coordinates followed by action. */
public class LUT implements CommonInterface {
    public static final int[] BINS = {3, 3, 3, 4, 2, 6};
    public static final int STATES = 216, ACTIONS = 6, SIZE = 1296;
    private final double[] q = new double[SIZE];
    private final int[] visits = new int[SIZE];
    public static int index(double[] x) {
        if (x.length != BINS.length) throw new IllegalArgumentException("6 coordinates required");
        int n = 0;
        for (int i = 0; i < x.length; i++) {
            int b = (int)x[i];
            if (x[i] != b || b < 0 || b >= BINS[i])
                throw new IllegalArgumentException("Invalid bin");
            n = n * BINS[i] + b;
        }
        return n;
    }
    public double output_for(double[] x) { return q[index(x)]; }
    public double train(double[] x, double target) {
        if (!Double.isFinite(target)) throw new IllegalArgumentException("Nonfinite target");
        int i = index(x);
        double error = target - q[i];
        q[i] = target; // RL controller already applies alpha.
        visits[i]++;
        return 0.5 * error * error;
    }
    public double value(int s, int a) { return q[s * ACTIONS + a]; }
    public double max(int s) {
        double m = Double.NEGATIVE_INFINITY;
        for (int a = 0; a < ACTIONS; a++) m = Math.max(m, value(s,a));
        return m;
    }
    public int choose(int s, double epsilon, Random rng) {
        if (rng.nextDouble() < epsilon) return rng.nextInt(ACTIONS);
        double best = max(s);
        int n = 0, chosen = 0;
        for (int a = 0; a < ACTIONS; a++)
            if (value(s,a) == best && rng.nextInt(++n) == 0) chosen = a;
        return chosen; // Uniform random tie-breaking, including epsilon=0.
    }
    public double update(int s, int a, double target, double alpha) {
        double[] x = decode(s * ACTIONS + a);
        double delta = target - output_for(x);
        train(x, output_for(x) + alpha * delta);
        return delta;
    }
    public static double[] decode(int n) {
        double[] x = new double[6];
        for (int i=5; i>=0; i--) { x[i] = n % BINS[i]; n /= BINS[i]; }
        return x;
    }
    public int covered() {
        int n=0; for (int v: visits) if (v>0) n++; return n;
    }
    public void save(String path) throws IOException {
        try (DataOutputStream out = new DataOutputStream(new RobocodeFileOutputStream(path))) {
            out.writeInt(0x4c555432); out.writeInt(SIZE);
            for (int i=0; i<SIZE; i++) { out.writeDouble(q[i]); out.writeInt(visits[i]); }
        }
    }
    public void load(String path) throws IOException {
        double[] temp = new double[SIZE]; int[] count = new int[SIZE];
        try (DataInputStream in = new DataInputStream(new FileInputStream(path))) {
            if (in.readInt()!=0x4c555432 || in.readInt()!=SIZE)
                throw new IOException("LUT format mismatch");
            for (int i=0; i<SIZE; i++) {
                temp[i]=in.readDouble(); count[i]=in.readInt();
                if (!Double.isFinite(temp[i]) || count[i]<0) throw new IOException("Invalid entry");
            }
            if (in.read()!=-1) throw new IOException("Trailing bytes");
        }
        System.arraycopy(temp,0,q,0,SIZE); System.arraycopy(count,0,visits,0,SIZE);
    }
}
