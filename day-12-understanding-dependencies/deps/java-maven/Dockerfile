FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /src
# Resolve and copy dependencies using only the POM: cached until pom.xml changes.
COPY pom.xml .
RUN mvn -B -q dependency:copy-dependencies -DoutputDirectory=target/lib
COPY src ./src
RUN mvn -B -q compile

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /src/target/lib ./lib
COPY --from=build /src/target/classes ./classes
CMD ["java", "-cp", "classes:lib/*", "hello.Main"]
