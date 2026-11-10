import java.net.InetAddress;

public class Hello {
    public static void main(String[] args) throws Exception {
        String name = System.getenv().getOrDefault("NAME", "world");
        // LOOP_SECONDS=0 (default): print once and exit.
        // LOOP_SECONDS=10: print every 10 seconds forever.
        int interval = Integer.parseInt(System.getenv().getOrDefault("LOOP_SECONDS", "0"));
        String host = InetAddress.getLocalHost().getHostName();
        while (true) {
            System.out.println("Hello, " + name + "! from Java "
                    + System.getProperty("java.version") + " on " + host);
            if (interval <= 0) {
                break;
            }
            Thread.sleep(interval * 1000L);
        }
    }
}
