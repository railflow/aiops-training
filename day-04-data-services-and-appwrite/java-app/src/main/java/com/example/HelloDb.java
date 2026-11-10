package com.example;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Statement;

/**
 * Writes one greeting row to Postgres and prints the latest rows.
 * Settings come from the same environment variables psql uses:
 * PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD.
 */
public class HelloDb {

    static String env(String key, String fallback) {
        String value = System.getenv(key);
        return (value == null || value.isEmpty()) ? fallback : value;
    }

    public static void main(String[] args) throws Exception {
        String url = "jdbc:postgresql://" + env("PGHOST", "localhost") + ":" + env("PGPORT", "5432")
                + "/" + env("PGDATABASE", "app");
        String name = env("NAME", "world");

        try (Connection conn = DriverManager.getConnection(url, env("PGUSER", "app"), env("PGPASSWORD", ""))) {
            try (Statement st = conn.createStatement()) {
                st.execute("CREATE TABLE IF NOT EXISTS greetings ("
                        + "id SERIAL PRIMARY KEY, name TEXT NOT NULL, message TEXT NOT NULL, "
                        + "source TEXT NOT NULL DEFAULT 'unknown', created_at TIMESTAMPTZ NOT NULL DEFAULT now())");
            }
            try (PreparedStatement ps = conn.prepareStatement(
                    "INSERT INTO greetings (name, message, source) VALUES (?, ?, ?)")) {
                ps.setString(1, name);
                ps.setString(2, "Hello, " + name + "!");
                ps.setString(3, "java");
                ps.executeUpdate();
            }
            try (Statement st = conn.createStatement();
                 ResultSet rs = st.executeQuery(
                         "SELECT id, source, name, message, created_at FROM greetings ORDER BY id DESC LIMIT 5")) {
                while (rs.next()) {
                    System.out.println(rs.getInt("id") + " | " + rs.getString("source") + " | "
                            + rs.getString("name") + " | " + rs.getString("message") + " | "
                            + rs.getTimestamp("created_at"));
                }
            }
        }
    }
}
