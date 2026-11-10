# Stage 1: compile with the full JDK.
FROM eclipse-temurin:21-jdk AS build
WORKDIR /src
COPY Hello.java .
RUN javac -d /out Hello.java

# Stage 2: run on the (smaller) JRE image. The compiler never ships.
FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /out/Hello.class .
CMD ["java", "-cp", "/app", "Hello"]
