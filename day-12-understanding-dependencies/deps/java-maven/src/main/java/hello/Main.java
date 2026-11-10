package hello;

import com.google.common.base.Joiner;
import org.apache.commons.lang3.StringUtils;

public class Main {
    public static void main(String[] args) {
        String joined = Joiner.on(" ").join("Hello", "from", "java");
        System.out.println(StringUtils.capitalize(joined) + " (Guava + commons-lang3 found on the classpath)");
    }
}
