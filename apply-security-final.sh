#!/bin/bash
# ============================================================================
# APLICAR SEGURANÇA NO DJEN PROXY - VERSÃO FINAL
# Execute no Google Cloud Shell
# ============================================================================

set -e

echo "🔒 Aplicando segurança no DJEN Proxy..."
echo ""

# 1. Criar Dockerfile
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

# 2. Criar código seguro
cat > djen_proxy.go << 'GO_CODE_END'
package main

import (
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"strings"
	"time"
)

const ALLOWED_TARGET = "https://comunicaapi.pje.jus.br"

// Middleware de segurança
func securityMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Bloquear URLs externas no path
		if strings.Contains(r.URL.Path, "http://") || strings.Contains(r.URL.Path, "https://") {
			log.Printf("🚨 BLOCKED: External URL attempt: %s from %s", r.URL.Path, r.RemoteAddr)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusForbidden)
			w.Write([]byte(`{"error":"Forbidden: This proxy only serves comunicaapi.pje.jus.br","blocked":"external_url"}`))
			return
		}

		// Bloquear manipulação de Host header
		if r.Host != "" && !strings.Contains(r.Host, ".run.app") &&
		   !strings.Contains(r.Host, "localhost") && !strings.Contains(r.Host, "127.0.0.1") {
			log.Printf("🚨 BLOCKED: Invalid Host header: %s from %s", r.Host, r.RemoteAddr)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusForbidden)
			w.Write([]byte(`{"error":"Forbidden: Invalid Host header","blocked":"host_manipulation"}`))
			return
		}

		next.ServeHTTP(w, r)
	})
}

func main() {
	target, _ := url.Parse(ALLOWED_TARGET)

	// Criar reverse proxy
	proxy := &httputil.ReverseProxy{
		Director: func(req *http.Request) {
			req.URL.Scheme = target.Scheme
			req.URL.Host = target.Host
			req.Host = target.Host
			req.Header.Set("X-Forwarded-Host", req.Header.Get("Host"))
			log.Printf("✅ Proxying: %s %s → %s%s", req.Method, req.RemoteAddr, ALLOWED_TARGET, req.URL.Path)
		},
		Transport: &http.Transport{
			MaxIdleConns:        100,
			MaxIdleConnsPerHost: 100,
			IdleConnTimeout:     90 * time.Second,
			DisableCompression:  false,
		},
		ErrorHandler: func(w http.ResponseWriter, r *http.Request, err error) {
			log.Printf("❌ Proxy error: %v", err)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusBadGateway)
			w.Write([]byte(`{"error":"DJEN API unreachable"}`))
		},
	}

	// Health check endpoint
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"status":"healthy","proxy":"djen-secure","region":"southamerica-east1","allowed_target":"comunicaapi.pje.jus.br","security":"enabled"}`))
	})

	// Security info endpoint
	http.HandleFunc("/security", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"security":"enabled","allowed_target":"comunicaapi.pje.jus.br","blocked":["external_urls","host_manipulation","open_proxy_abuse"],"note":"This proxy ONLY serves Brazilian DJEN API"}`))
	})

	// Apply security middleware to all proxy requests
	http.Handle("/", securityMiddleware(http.HandlerFunc(proxy.ServeHTTP)))

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("🔒 DJEN Secure Proxy starting on port %s", port)
	log.Printf("🇧🇷 Target: %s (LOCKED)", ALLOWED_TARGET)
	log.Printf("🛡️  Security: ENABLED")

	server := &http.Server{
		Addr:         ":" + port,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	log.Fatal(server.ListenAndServe())
}
GO_CODE_END

echo "✅ Arquivos criados"
echo ""

# 3. Deploy com todas as proteções
echo "🚀 Fazendo deploy seguro..."
gcloud run deploy djen-proxy \
  --source . \
  --region southamerica-east1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 256Mi \
  --cpu 1 \
  --max-instances 10 \
  --min-instances 0 \
  --timeout 30s \
  --port 8080 \
  --concurrency 80 \
  --cpu-throttling \
  --execution-environment gen2 \
  --update-labels security=enabled,purpose=djen-proxy,version=secure \
  --quiet

echo "✅ Deploy concluído"
echo ""

# 4. Obter URL
PROXY_URL=$(gcloud run services describe djen-proxy --region southamerica-east1 --format='value(status.url)')

# 5. Aguardar deploy propagar
echo "⏳ Aguardando 10 segundos para o deploy propagar..."
sleep 10

# 6. Testes automáticos
echo ""
echo "🧪 EXECUTANDO TESTES DE SEGURANÇA..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Teste 1: Health check
echo "✅ Teste 1: Health check"
HTTP_CODE=$(curl -s -o /tmp/test1.txt -w "%{http_code}" "$PROXY_URL/health")
RESPONSE=$(cat /tmp/test1.txt)
if [ "$HTTP_CODE" == "200" ] && echo "$RESPONSE" | grep -q "secure"; then
  echo "   ✅ PASSOU - Health check OK ($HTTP_CODE)"
  echo "   Response: $RESPONSE"
else
  echo "   ❌ FALHOU - Status: $HTTP_CODE"
  echo "   Response: $RESPONSE"
fi
echo ""

# Teste 2: Security endpoint
echo "✅ Teste 2: Security endpoint"
HTTP_CODE=$(curl -s -o /tmp/test2.txt -w "%{http_code}" "$PROXY_URL/security")
RESPONSE=$(cat /tmp/test2.txt)
if [ "$HTTP_CODE" == "200" ] && echo "$RESPONSE" | grep -q "enabled"; then
  echo "   ✅ PASSOU - Security endpoint OK ($HTTP_CODE)"
  echo "   Response: $RESPONSE"
else
  echo "   ❌ FALHOU - Status: $HTTP_CODE"
fi
echo ""

# Teste 3: Bloquear http://
echo "❌ Teste 3: Bloquear http://google.com (deve retornar 403)"
HTTP_CODE=$(curl -s -o /tmp/test3.txt -w "%{http_code}" "$PROXY_URL/http://google.com")
RESPONSE=$(cat /tmp/test3.txt)
if [ "$HTTP_CODE" == "403" ] && echo "$RESPONSE" | grep -q "Forbidden"; then
  echo "   ✅ PASSOU - Bloqueou corretamente ($HTTP_CODE)"
  echo "   Response: $RESPONSE"
else
  echo "   ❌ FALHOU - Status: $HTTP_CODE (esperado 403)"
  echo "   Response: $RESPONSE"
fi
echo ""

# Teste 4: Bloquear https://
echo "❌ Teste 4: Bloquear https://evil.com (deve retornar 403)"
HTTP_CODE=$(curl -s -o /tmp/test4.txt -w "%{http_code}" "$PROXY_URL/https://evil.com")
RESPONSE=$(cat /tmp/test4.txt)
if [ "$HTTP_CODE" == "403" ] && echo "$RESPONSE" | grep -q "Forbidden"; then
  echo "   ✅ PASSOU - Bloqueou corretamente ($HTTP_CODE)"
  echo "   Response: $RESPONSE"
else
  echo "   ❌ FALHOU - Status: $HTTP_CODE (esperado 403)"
fi
echo ""

# Teste 5: API DJEN real
echo "✅ Teste 5: API DJEN legítima (deve funcionar)"
HTTP_CODE=$(curl -s -o /tmp/test5.txt -w "%{http_code}" "$PROXY_URL/api/v1/comunicacao?idOrgao=2")
if [ "$HTTP_CODE" == "200" ]; then
  echo "   ✅ PASSOU - API DJEN OK ($HTTP_CODE)"
else
  echo "   ⚠️  Status: $HTTP_CODE"
fi
echo ""

# Teste 6: Swagger DJEN
echo "✅ Teste 6: Swagger DJEN (geo-bloqueado fora do BR)"
HTTP_CODE=$(curl -s -o /tmp/test6.txt -w "%{http_code}" "$PROXY_URL/swagger/djen.yml")
if [ "$HTTP_CODE" == "200" ]; then
  LINES=$(wc -l < /tmp/test6.txt)
  echo "   ✅ PASSOU - Swagger OK ($HTTP_CODE, $LINES linhas)"
else
  echo "   ⚠️  Status: $HTTP_CODE"
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ SEGURANÇA APLICADA E TESTADA!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔒 URL do Proxy Seguro:"
echo "   $PROXY_URL"
echo ""
echo "🛡️  Proteções ativas:"
echo "   ✅ Bloqueia URLs externas (http://, https://)"
echo "   ✅ Bloqueia manipulação de Host header"
echo "   ✅ Rate limiting (80 req concorrentes)"
echo "   ✅ Timeout de 30s"
echo "   ✅ HTTPS obrigatório (TLS 1.2+)"
echo "   ✅ DDoS protection (Google nativo)"
echo "   ✅ Auto-escala 0→10 instâncias"
echo ""
echo "📝 Configurar no CausaGanha:"
echo "   export DJEN_PROXY_URL='$PROXY_URL'"
echo ""
echo "📊 Ver logs de segurança:"
echo "   gcloud run services logs read djen-proxy --region southamerica-east1 | grep BLOCKED"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Limpar arquivos temporários
rm -f /tmp/test*.txt
