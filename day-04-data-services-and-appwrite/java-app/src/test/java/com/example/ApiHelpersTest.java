package com.example;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class ApiHelpersTest {

    @Test
    void escapesQuotesAndBackslashes() {
        assertEquals("a\\\"b\\\\c", Api.jsonEscape("a\"b\\c"));
    }

    @Test
    void escapesNewlines() {
        assertEquals("line1\\nline2", Api.jsonEscape("line1\nline2"));
    }

    @Test
    void versionJsonNamesTheService() {
        String json = Api.versionJson();
        org.junit.jupiter.api.Assertions.assertTrue(json.contains("\"service\":\"hello-java\""));
        org.junit.jupiter.api.Assertions.assertTrue(json.contains("\"version\""));
    }
}
