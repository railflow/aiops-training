package com.example;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

class GreeterTest {

    @Test
    void greetsByName() {
        assertEquals("Hello, Ada!", Greeter.greeting("Ada"));
    }

    @Test
    void trimsWhitespace() {
        assertEquals("Hello, Ada!", Greeter.greeting("  Ada  "));
    }

    @Test
    void nullBecomesWorld() {
        assertEquals("Hello, world!", Greeter.greeting(null));
    }

    @ParameterizedTest
    @ValueSource(strings = {"", " ", "   "})
    void blankBecomesWorld(String name) {
        assertEquals("Hello, world!", Greeter.greeting(name));
    }
}
