# Stage 1: Maven build. Copying pom.xml first lets Docker cache the dependency download
# until the pom changes (see Day 2: put rarely-changing steps first).
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /src
COPY pom.xml .
RUN mvn -q -B dependency:go-offline
COPY src ./src
RUN mvn -q -B package -DskipTests

# Stage 2: just a JRE and the shaded (fat) jar.
FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /src/target/app.jar /app/app.jar
EXPOSE 8080
CMD ["java", "-cp", "/app/app.jar", "com.example.Api"]
