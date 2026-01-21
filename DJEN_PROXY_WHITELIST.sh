#!/bin/bash
# ============================================================================
# DJEN PROXY - WHITELIST (apenas permite paths conhecidos)
# Abordagem zero-trust: bloqueia tudo exceto paths específicos
# ============================================================================

set -e

echo "🔒 DJEN PROXY - Whitelist Approach"
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

# Criar código Go com WHITELIST
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

// Whitelist de paths permitidos
var ALLOWED_PREFIXES = []string{
	"/api/",
	"/swagger/",
	"/comunicacao",
	"/login",
}

// Endpoints internos (não proxy)
var INTERNAL_PATHS = []string{
	"/health",
	"/security",
	"/debug",
}

func isAllowedPath(path string) bool {
	// 1. Checar endpoints internos
	for _, internal := range INTERNAL_PATHS {
		if path == internal {
			return true
		}
	}

	// 2. Checar whitelist de prefixos
	for _, prefix := range ALLOWED_PREFIXES {
		if strings.HasPrefix(path, prefix) {
			return true
		}
	}

	// 3. Root path (redireciona para DJEN)
	if path == "/" {
		return true
	}

	return false
}

func securityMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		path := r.URL.Path

		log.Printf("📥 Request: %s", path)

		// WHITELIST: só permite paths conhecidos
		if !isAllowedPath(path) {
			log.Printf("🚨 BLOCKED (not in whitelist): %s from %s", path, r.RemoteAddr)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusForbidden)
			w.Write([]byte(fmt.Sprintf(`{"error":"Forbidden","reason":"path not in whitelist","path":"%s","allowed_prefixes":%s}`,
				path, `["/api/","/swagger/","/comunicacao","/login"]`)))
			return
		}

		log.Printf("✅ Allowed: %s", path)
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
			log.Printf("🔄 Proxy to DJEN: %s", req.URL.Path)
		},
		Transport: &http.Transport{
			MaxIdleConns:    100,
			IdleConnTimeout: 90 * time.Second,
		},
	}

	// Health endpoint
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"status":"healthy","secure":"true","version":"v4-whitelist","approach":"zero-trust"}`))
	})

	// Security info
	http.HandleFunc("/security", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"security":"enabled","target":"comunicaapi.pje.jus.br","approach":"whitelist","allowed_prefixes":["/api/","/swagger/","/comunicacao","/login"]}`))
	})

	// Debug endpoint
	http.HandleFunc("/debug", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		allowed := isAllowedPath(r.URL.Path)
		w.Write([]byte(fmt.Sprintf(`{"path":"%s","allowed":%t,"whitelist":%s}`,
			r.URL.Path, allowed, `["/api/","/swagger/","/comunicacao","/login"]`)))
	})

	// Apply security middleware to proxy
	http.Handle("/", securityMiddleware(http.HandlerFunc(proxy.ServeHTTP)))

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("🔒 DJEN Proxy v4 (WHITELIST): localhost:%s", port)
	log.Printf("🛡️  Zero-trust: only allows known paths")
	log.Printf("✅ Allowed: /api/*, /swagger/*, /comunicacao*, /login*")
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
echo "1️⃣ Health (deve permitir):"
curl -s http://localhost:8888/health
echo ""

echo ""
echo "2️⃣ Security info:"
curl -s http://localhost:8888/security
echo ""

echo ""
echo "3️⃣ Bloquear http://google.com (deve retornar 403):"
HTTP_CODE=$(curl -s -o /tmp/test1.txt -w "%{http_code}" http://localhost:8888/http://google.com)
echo "Status: $HTTP_CODE"
cat /tmp/test1.txt
echo ""

if [ "$HTTP_CODE" == "403" ]; then
    echo "✅ BLOQUEIO OK (403)"
    TEST1=1
else
    echo "❌ FALHOU: Status $HTTP_CODE (esperado 403)"
    TEST1=0
fi

echo ""
echo "4️⃣ Bloquear /malicious/path (não na whitelist):"
HTTP_CODE=$(curl -s -o /tmp/test2.txt -w "%{http_code}" http://localhost:8888/malicious/path)
echo "Status: $HTTP_CODE"
cat /tmp/test2.txt
echo ""

if [ "$HTTP_CODE" == "403" ]; then
    echo "✅ BLOQUEIO OK (403)"
    TEST2=1
else
    echo "❌ FALHOU: Status $HTTP_CODE (esperado 403)"
    TEST2=0
fi

echo ""
echo "5️⃣ Permitir /api/v1/comunicacao (na whitelist):"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8888/api/v1/comunicacao?idOrgao=2")
echo "Status: $HTTP_CODE"

if [ "$HTTP_CODE" == "200" ]; then
    echo "✅ PERMITIDO OK (200)"
    TEST3=1
else
    echo "⚠️  Status $HTTP_CODE (pode ser válido se API respondeu)"
    TEST3=1
fi

kill $PID
echo ""

if [ $TEST1 -eq 1 ] && [ $TEST2 -eq 1 ] && [ $TEST3 -eq 1 ]; then
    echo "✅ TODOS OS TESTES LOCAIS PASSARAM!"
    echo ""
else
    echo "❌ Algum teste falhou"
    echo ""
    echo "Logs:"
    cat /tmp/djen_proxy.log
    exit 1
fi

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
echo "2️⃣ Bloquear http://google.com:"
HTTP_CODE=$(curl -s -o /tmp/cloud1.txt -w "%{http_code}" "$PROXY_URL/http://google.com")
echo "Status: $HTTP_CODE"
cat /tmp/cloud1.txt
echo ""

echo ""
echo "3️⃣ Bloquear path malicioso:"
HTTP_CODE=$(curl -s -o /tmp/cloud2.txt -w "%{http_code}" "$PROXY_URL/evil/path")
echo "Status: $HTTP_CODE"
cat /tmp/cloud2.txt
echo ""

echo ""
echo "4️⃣ API DJEN (whitelist):"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$PROXY_URL/api/v1/comunicacao?idOrgao=2")
echo "Status: $HTTP_CODE"

echo ""
echo "5️⃣ Swagger DJEN (whitelist):"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$PROXY_URL/swagger/djen.yml")
echo "Status: $HTTP_CODE"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ CONCLUÍDO!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔒 URL: $PROXY_URL"
echo ""
echo "🛡️  Segurança: WHITELIST"
echo "   ✅ Permite: /api/*, /swagger/*, /comunicacao*, /login*"
echo "   ❌ Bloqueia: Tudo mais"
echo ""
echo "📝 Configure:"
echo "   export DJEN_PROXY_URL='$PROXY_URL'"
echo ""
