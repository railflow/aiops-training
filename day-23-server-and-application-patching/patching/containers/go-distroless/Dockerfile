# Build context: ../../../../day-07-traefik-ingress/go-api   (the Go API from Day 7)
# A static Go binary needs no OS userland at all. "static-debian12:nonroot" has CA certificates, tzdata
# and a non-root user, and no shell and no package manager. Digest read 2026-11-05: refresh it.
FROM golang:1.23 AS build
WORKDIR /src
COPY go.mod .
COPY main.go .
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /goapi .

FROM gcr.io/distroless/static-debian12:nonroot@sha256:afa5c872c891853ca7fcf1f12c3edb23f7eeef36189728842dd51042ff57f7ab
COPY --from=build /goapi /goapi
EXPOSE 8080
USER nonroot:nonroot
ENTRYPOINT ["/goapi"]
