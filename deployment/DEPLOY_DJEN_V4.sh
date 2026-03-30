#!/bin/bash
# ============================================================================
# DJEN PROXY - Deploy Script
# VERSÃO: v4.0 (2026-01-21 17:40 UTC)
# MELHORIAS: Graceful shutdown, melhor error handling
# ============================================================================

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 DJEN PROXY - Deploy Script"
echo "📌 VERSÃO: v4.0 (2026-01-21 17:40)"
echo "✨ NOVO: Graceful shutdown + Better error handling"
echo "🗑️  MODO: AUTO-DELETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. CRIAR CÓDIGO GO MELHORADO
echo "📝 Criando djen_proxy.go (v4 - melhorado)..."
cat > djen_proxy.go << 'GO'
package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"
)

const TARGET = "https://comunicaapi.pje.jus.br"

var WHITELIST = []string{"/api/", "/swagger/", "/comunicacao", "/login"}

func allowed(path string) bool {
	if path == "/" || path == "/health" || path == "/security" {
		return true
	}
	for _, p := range WHITELIST {
		if strings.HasPrefix(path, p) {
			return true
		}
	}
	return false
}

func security(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !allowed(r.URL.Path) {
			log.Printf("🚨 BLOCKED: %s from %s", r.URL.Path, r.RemoteAddr)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusForbidden)
			w.Write([]byte(fmt.Sprintf(`{"error":"forbidden","path":"%s"}`, r.URL.Path)))
			return
		}
		next.ServeHTTP(w, r)
	})
}

func main() {
	target, err := url.Parse(TARGET)
	if err != nil {
		log.Fatalf("❌ Invalid target URL: %v", err)
	}

	proxy := &httputil.ReverseProxy{
		Director: func(r *http.Request) {
			r.URL.Scheme = target.Scheme
			r.URL.Host = target.Host
			r.Host = target.Host
		},
		Transport: &http.Transport{
			MaxIdleConns:        100,
			MaxIdleConnsPerHost: 100,
			IdleConnTimeout:     90 * time.Second,
		},
	}

	mux := http.NewServeMux()

	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"status":"ok","version":"v4.0"}`))
	})

	mux.HandleFunc("/security", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"whitelist":["/api/","/swagger/","/comunicacao","/login"],"version":"v4.0"}`))
	})

	mux.Handle("/", security(http.HandlerFunc(proxy.ServeHTTP)))

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	server := &http.Server{
		Addr:         ":" + port,
		Handler:      mux,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	// Graceful shutdown
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	go func() {
		log.Printf("🔒 DJEN Proxy v4.0 starting on :%s", port)
		log.Printf("🛡️  Whitelist: %v", WHITELIST)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("❌ Server error: %v", err)
		}
	}()

	<-ctx.Done()
	log.Println("🛑 Shutdown signal received")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := server.Shutdown(shutdownCtx); err != nil {
		log.Printf("❌ Shutdown error: %v", err)
	} else {
		log.Println("✅ Server stopped gracefully")
	}
}
GO

# 2. CRIAR DOCKERFILE
echo "📝 Criando Dockerfile..."
cat > Dockerfile << 'DOCKER'
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY djen_proxy.go .
RUN go build -o djen_proxy djen_proxy.go

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/djen_proxy .
EXPOSE 8080
CMD ["./djen_proxy"]
DOCKER

echo "✅ Arquivos criados (código melhorado)"
echo ""

# 3. DELETAR SERVIÇO EXISTENTE
if gcloud run services describe djen-proxy --region southamerica-east1 &>/dev/null; then
    echo "🗑️  Deletando serviço existente..."
    gcloud run services delete djen-proxy --region southamerica-east1 --quiet
    echo "✅ Deletado"
    echo ""
fi

# 4. DEPLOY
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 DEPLOY (v4.0 - Graceful Shutdown)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

gcloud run deploy djen-proxy \
  --source . \
  --region southamerica-east1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --max-instances 10 \
  --timeout 30s

# 5. PEGAR URL
URL=$(gcloud run services describe djen-proxy --region southamerica-east1 --format='value(status.url)')

# 6. TESTAR
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ DEPLOY CONCLUÍDO!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔗 URL: $URL"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 TESTANDO PROXY..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "1️⃣ Health (deve mostrar v4.0):"
curl -s $URL/health
echo ""

echo ""
echo "2️⃣ Bloqueio /evil (deve retornar 403):"
curl -s $URL/evil
echo ""

echo ""
echo "3️⃣ API DJEN (deve funcionar):"
curl -s -o /dev/null -w "Status: %{http_code}" "$URL/api/v1/comunicacao?idOrgao=2"
echo ""

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 CONFIGURAÇÃO"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "export DJEN_PROXY_URL='$URL'"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ CONCLUÍDO - v4.0"
echo "✨ Melhorias: Graceful shutdown, error handling"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
