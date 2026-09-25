FROM golang:1.24-alpine AS builder
WORKDIR /app
COPY go.mod djen_proxy.go .
RUN go build -o djen_proxy .

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/djen_proxy .
EXPOSE 8080
CMD ["./djen_proxy"]
