# Stage 1: build a static binary with the Go toolchain.
FROM golang:1.23 AS build
WORKDIR /src
COPY go.mod .
COPY main.go .
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /hello .

# Stage 2: an empty image. Only the binary ships: no shell, no package manager.
FROM scratch
COPY --from=build /hello /hello
ENTRYPOINT ["/hello"]
