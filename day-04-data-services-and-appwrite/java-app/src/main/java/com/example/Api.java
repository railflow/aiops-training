package com.example;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.HashMap;
import java.util.Map;

/**
 * A tiny REST API using only the JDK's built-in HTTP server.
 *
 * GET  /              greeting (also /hello); optional ?name=
 * GET  /healthz       liveness: the process is up (no dependencies checked)
 * GET  /readyz        readiness: with PGHOST set, checks the database; 503 if it is unreachable
 * GET  /version       which build is running (APP_VERSION and GIT_SHA environment variables)
 * GET  /greetings     latest stored greetings (needs PGHOST; otherwise an empty list)
 * POST /greetings     store a greeting: ?name=Ada (needs PGHOST)
 */
public class Api {

    static String host() {
        try {
            return InetAddress.getLocalHost().getHostName();
        } catch (Exception e) {
            return "unknown";
        }
    }

    static String jsonEscape(String s) {
        return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r");
    }

    static Map<String, String> query(HttpExchange ex) {
        Map<String, String> params = new HashMap<>();
        String raw = ex.getRequestURI().getRawQuery();
        if (raw == null || raw.isEmpty()) {
            return params;
        }
        for (String pair : raw.split("&")) {
            String[] kv = pair.split("=", 2);
            params.put(URLDecoder.decode(kv[0], StandardCharsets.UTF_8),
                    kv.length > 1 ? URLDecoder.decode(kv[1], StandardCharsets.UTF_8) : "");
        }
        return params;
    }

    static void send(HttpExchange ex, int status, String json) throws IOException {
        System.out.println(ex.getRequestMethod() + " " + ex.getRequestURI() + " from "
                + ex.getRemoteAddress().getAddress().getHostAddress() + " -> " + status);
        byte[] body = json.getBytes(StandardCharsets.UTF_8);
        ex.getResponseHeaders().set("Content-Type", "application/json");
        ex.sendResponseHeaders(status, body.length);
        try (OutputStream os = ex.getResponseBody()) {
            os.write(body);
        }
    }

    static boolean useDb() {
        return !HelloDb.env("PGHOST", "").isEmpty();
    }

    static Connection connect() throws Exception {
        String url = "jdbc:postgresql://" + HelloDb.env("PGHOST", "localhost") + ":" + HelloDb.env("PGPORT", "5432")
                + "/" + HelloDb.env("PGDATABASE", "app");
        return DriverManager.getConnection(url, HelloDb.env("PGUSER", "app"), HelloDb.env("PGPASSWORD", ""));
    }

    static String greetingsJson() throws Exception {
        StringBuilder sb = new StringBuilder("{\"greetings\":[");
        if (useDb()) {
            try (Connection c = connect(); Statement st = c.createStatement();
                 ResultSet rs = st.executeQuery(
                         "SELECT id, source, name, message FROM greetings ORDER BY id DESC LIMIT 20")) {
                boolean first = true;
                while (rs.next()) {
                    if (!first) {
                        sb.append(',');
                    }
                    first = false;
                    sb.append("{\"id\":").append(rs.getInt("id"))
                            .append(",\"source\":\"").append(jsonEscape(rs.getString("source")))
                            .append("\",\"name\":\"").append(jsonEscape(rs.getString("name")))
                            .append("\",\"message\":\"").append(jsonEscape(rs.getString("message"))).append("\"}");
                }
            }
        }
        return sb.append("]}").toString();
    }

    static void store(String name) throws Exception {
        try (Connection c = connect(); PreparedStatement ps = c.prepareStatement(
                "INSERT INTO greetings (name, message, source) VALUES (?, ?, 'java-api')")) {
            ps.setString(1, name.isEmpty() ? "world" : name);
            ps.setString(2, Greeter.greeting(name));
            ps.executeUpdate();
        }
    }

    static String versionJson() {
        return "{\"service\":\"hello-java\",\"version\":\"" + jsonEscape(HelloDb.env("APP_VERSION", "dev"))
                + "\",\"commit\":\"" + jsonEscape(HelloDb.env("GIT_SHA", "unknown")) + "\"}";
    }

    public static void main(String[] args) throws Exception {
        int port = Integer.parseInt(HelloDb.env("PORT", "8080"));
        String pod = host();
        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);

        server.createContext("/", ex -> {
            String name = query(ex).get("name");
            send(ex, 200, "{\"message\":\"" + jsonEscape(Greeter.greeting(name))
                    + "\",\"served_by\":\"java\",\"pod\":\"" + jsonEscape(pod) + "\"}");
        });
        server.createContext("/healthz", ex -> send(ex, 200, "{\"status\":\"ok\"}"));
        server.createContext("/readyz", ex -> {
            if (!useDb()) {
                send(ex, 200, "{\"status\":\"ready\",\"database\":\"not configured\"}");
                return;
            }
            try {
                greetingsJson();
                send(ex, 200, "{\"status\":\"ready\",\"database\":\"ok\"}");
            } catch (Exception e) {
                send(ex, 503, "{\"status\":\"not ready\",\"database\":\"unavailable\"}");
            }
        });
        server.createContext("/version", ex -> send(ex, 200, versionJson()));
        server.createContext("/greetings", ex -> {
            try {
                if ("POST".equals(ex.getRequestMethod())) {
                    String name = query(ex).getOrDefault("name", "");
                    if (!useDb()) {
                        send(ex, 503, "{\"error\":\"PGHOST is not set\"}");
                        return;
                    }
                    store(name);
                    send(ex, 201, "{\"message\":\"" + jsonEscape(Greeter.greeting(name)) + "\",\"stored\":\"postgres\"}");
                } else {
                    send(ex, 200, greetingsJson());
                }
            } catch (Exception e) {
                send(ex, 500, "{\"error\":\"" + jsonEscape(String.valueOf(e.getMessage())) + "\"}");
            }
        });

        server.start();
        System.out.println("Java API listening on port " + port);
    }
}
