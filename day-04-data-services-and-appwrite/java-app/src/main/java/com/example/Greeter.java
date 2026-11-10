package com.example;

/** Pure greeting logic, kept separate from HTTP and database code so it is easy to test. */
public final class Greeter {

    private Greeter() {
    }

    public static String greeting(String name) {
        String cleaned = name == null ? "" : name.trim();
        return "Hello, " + (cleaned.isEmpty() ? "world" : cleaned) + "!";
    }
}
