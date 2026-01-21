#!/bin/bash
# ============================================================================
# DJEN PROXY - CORREÇÃO FINAL (usa RequestURI em vez de Path)
# ============================================================================

set -e

echo "🔧 DJEN PROXY - Correção do bloqueio"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Criar Dockerfile
cat > Dockerfile << 'DOCKERFILE_END'
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
DOCKERFILE_END

# Criar código Go CORRIGIDO (usa RequestURI)
cat > djen_proxy.go << 'GO_END'
package main

import (
	"fmt"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"strings"
	"time"
)

const ALLOWED_TARGET = "https://comunicaapi.pje.jus.br"

func securityMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// IMPORTANTE: Usar RequestURI (RAW) em vez de Path (normalizado)
		uri := r.RequestURI

		log.Printf("📥 Request: uri=%s (raw)", uri)

		// Bloquear URLs externas (usa RequestURI que é RAW)
		if strings.Contains(uri, "http://") || strings.Contains(uri, "https://") {
			log.Printf("🚨 BLOCKED: uri=%s", uri)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusForbidden)
			w.Write([]byte(fmt.Sprintf(`{"error":"Forbidden: DJEN only","blocked_uri":"%s","reason":"external_url"}`, uri)))
			return
		}

		next.ServeHTTP(w, r)
	})
}

func main() {
	target, _ := url.Parse(ALLOWED_TARGET)

	proxy := &httputil.ReverseProxy{
		Director: func(req *http.Request) {
			req.URL.Scheme = target.Scheme
			req.URL.Host = target.Host
			req.Host = target.Host
			log.Printf("✅ Proxy: %s", req.URL.Path)
		},
		Transport: &http.Transport{MaxIdleConns: 100, IdleConnTimeout: 90 * time.Second},
	}

	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"status":"healthy","secure":"true","version":"v3-fixed"}`))
	})

	http.HandleFunc("/security", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"security":"enabled","target":"comunicaapi.pje.jus.br","blocks":["external_urls"],"uses":"RequestURI"}`))
	})

	http.HandleFunc("/debug", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(fmt.Sprintf(`{"path":"%s","uri":"%s","host":"%s","note":"using RequestURI (raw)"}`, r.URL.Path, r.RequestURI, r.Host)))
	})

	http.Handle("/", securityMiddleware(http.HandlerFunc(proxy.ServeHTTP)))

	port := os.Getenv("PORT")
	if port == "" { port = "8080" }

	log.Printf("🔒 DJEN Proxy v3 (FIXED): localhost:%s", port)
	log.Printf("🛡️  Using RequestURI (raw) for blocking")
	http.ListenAndServe(":"+port, nil)
}
GO_END

echo "✅ Arquivos criados"
echo ""

# TESTE LOCAL
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 FASE 1: TESTE LOCAL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

go build -o djen_proxy djen_proxy.go
PORT=8888 ./djen_proxy > /tmp/djen_proxy.log 2>&1 &
PID=$!
echo "✅ Proxy rodando no PID $PID (porta 8888)"
sleep 2

echo ""
echo "1️⃣ Health check:"
curl -s http://localhost:8888/health
echo ""

echo ""
echo "2️⃣ Debug endpoint:"
curl -s http://localhost:8888/debug
echo ""

echo ""
echo "3️⃣ Bloquear http://google.com (deve retornar 403):"
HTTP_CODE=$(curl -s -o /tmp/test.txt -w "%{http_code}" http://localhost:8888/http://google.com)
echo "Status: $HTTP_CODE"
cat /tmp/test.txt
echo ""

if [ "$HTTP_CODE" == "403" ]; then
    echo "✅ BLOQUEIO FUNCIONOU!"
    BLOCK_OK=1
else
    echo "❌ BLOQUEIO FALHOU! Status: $HTTP_CODE"
    echo ""
    echo "Logs:"
    tail -20 /tmp/djen_proxy.log
    BLOCK_OK=0
fi

kill $PID
echo ""

if [ $BLOCK_OK -eq 0 ]; then
    echo "❌ Teste local falhou. NÃO fazendo deploy."
    exit 1
fi

echo "✅ Teste local passou!"
echo ""

# PERGUNTAR DEPLOY
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
read -p "🚀 Deploy no Cloud Run? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deploy cancelado"
    exit 0
fi

# DEPLOY
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 FASE 2: DEPLOY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

gcloud run deploy djen-proxy \
  --source . \
  --region southamerica-east1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --max-instances 10 \
  --timeout 30s \
  --concurrency 80 \
  --quiet

PROXY_URL=$(gcloud run services describe djen-proxy --region southamerica-east1 --format='value(status.url)')

echo ""
echo "✅ Deploy concluído!"
echo ""

# TESTE CLOUD RUN
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 FASE 3: TESTE NO CLOUD RUN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "URL: $PROXY_URL"
echo ""
echo "Aguardando 10s..."
sleep 10

echo ""
echo "1️⃣ Health:"
curl -s $PROXY_URL/health
echo ""

echo ""
echo "2️⃣ Debug:"
curl -s $PROXY_URL/debug
echo ""

echo ""
echo "3️⃣ Bloquear http://google.com:"
HTTP_CODE=$(curl -s -o /tmp/cloud_test.txt -w "%{http_code}" "$PROXY_URL/http://google.com")
echo "Status: $HTTP_CODE"
cat /tmp/cloud_test.txt
echo ""

if [ "$HTTP_CODE" == "403" ]; then
    echo "✅ BLOQUEIO FUNCIONOU NO CLOUD RUN!"
else
    echo "❌ BLOQUEIO FALHOU NO CLOUD RUN!"
    echo ""
    echo "Logs:"
    gcloud run services logs read djen-proxy --region southamerica-east1 --limit 30
fi

echo ""
echo "4️⃣ API DJEN:"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$PROXY_URL/api/v1/comunicacao?idOrgao=2")
echo "Status: $HTTP_CODE"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ CONCLUÍDO!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔒 URL: $PROXY_URL"
echo ""
echo "📝 Configure:"
echo "   export DJEN_PROXY_URL='$PROXY_URL'"
echo ""
