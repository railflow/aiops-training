FROM golang:1.23 AS build
WORKDIR /src
COPY go.mod .
COPY main.go .
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /goapi .

FROM scratch
COPY --from=build /goapi /goapi
EXPOSE 8080
ENTRYPOINT ["/goapi"]
