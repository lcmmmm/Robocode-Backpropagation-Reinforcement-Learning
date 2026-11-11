package lutbot;
import java.io.IOException;
/** Same method names and scalar-regression semantics as Part 1. */
public interface CommonInterface {
    void load(String path) throws IOException;
    void save(String path) throws IOException;
    double train(double[] x, double target);
    double output_for(double[] x);
}
