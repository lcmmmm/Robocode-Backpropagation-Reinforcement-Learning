import lutbot.LUT;
import java.io.*;
import java.nio.file.*;
import java.util.*;
/** Deterministic checks of LUT indexing, TD arithmetic, policy and persistence. */
public class LUTChecks {
    private static void check(boolean ok, String label) {
        if (!ok) throw new AssertionError(label);
    }
    public static void main(String[] args) throws Exception {
        LUT q=new LUT();
        for(int i=0;i<LUT.SIZE;i++) check(LUT.index(LUT.decode(i))==i,"index round-trip");
        double[] x=LUT.decode(0);
        check(q.train(x,2)==2 && q.output_for(x)==2,"Part 1 error semantics");
        check(q.update(0,0,10,0.1)==8 && Math.abs(q.value(0,0)-2.8)<1e-12,"TD update");
        q.train(LUT.decode(6),5); q.train(LUT.decode(7),1);
        // With r=2 and gamma=.95: Q target=6.75, SARSA(a'=1) target=2.95.
        double qTarget=2+.95*q.max(1), sTarget=2+.95*q.value(1,1);
        check(Math.abs(qTarget-6.75)<1e-12 && Math.abs(sTarget-2.95)<1e-12,"bootstrap targets");
        q.update(0,0,-10,1);
        check(q.value(0,0)==-10,"terminal target without bootstrap");
        Random rng=new Random(5);
        for(int i=0;i<1000;i++) check(q.choose(1,0,rng)==0,"greedy policy");
        int[] n=new int[6]; for(int i=0;i<60000;i++) n[q.choose(1,1,rng)]++;
        for(int v:n) check(v>9500 && v<10500,"uniform exploration");
        LUT tied=new LUT(); Arrays.fill(n,0);
        for(int i=0;i<60000;i++) n[tied.choose(0,0,rng)]++;
        for(int v:n) check(v>9500 && v<10500,"unbiased greedy ties");
        Path file=Files.createTempFile("lut-check",".bin");
        LUT restored=new LUT(); restored.load(args[0]);
        try (DataInputStream in=new DataInputStream(new FileInputStream(args[0]))) {
            check(in.readInt()==0x4c555432 && in.readInt()==1296,"saved header");
            int covered=0;
            for(int i=0;i<LUT.SIZE;i++) {
                double expected=in.readDouble(); int count=in.readInt();
                check(expected==restored.output_for(LUT.decode(i)),"saved values");
                if(count>0) covered++;
            }
            check(covered==restored.covered(),"saved visits");
        }
        check(Files.size(Paths.get(args[0]))==15560,"binary size");
        double previous=restored.value(1,0);
        Files.write(file,new byte[]{0,1,2});
        try {restored.load(file.toString()); throw new AssertionError("corruption accepted");}
        catch(IOException expected) {}
        check(restored.value(1,0)==previous,"failed load leaves model intact");
        try {LUT.index(new double[]{3,0,0,0,0,0}); throw new AssertionError("invalid bin accepted");}
        catch(IllegalArgumentException expected) {}
        Files.delete(file);
        System.out.println("PASS: indexing, error semantics, TD targets, terminal update, epsilon policy, tie breaking, save/load, corrupt-file rejection");
    }
}
