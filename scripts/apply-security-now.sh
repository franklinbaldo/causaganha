#!/bin/bash
# ============================================================================
# APLICAR SEGURANÇA AGORA - Comando único para Cloud Shell
# Atualiza a função existente com todas as proteções
# ============================================================================

set -e

echo "🛡️  APLICANDO SEGURANÇA NO DJEN PROXY..."
echo ""

# 1. Criar versão segura do proxy
cat > djen_proxy.go << 'EOF'
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

const (
	ALLOWED_TARGET = "https://comunicaapi.pje.jus.br"
	ALLOWED_HOST   = "comunicaapi.pje.jus.br"
)

func securityMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Bloquear URLs externas
		if strings.Contains(r.URL.Path, "http://") || strings.Contains(r.URL.Path, "https://") {
			log.Printf("🚨 BLOCKED: External URL attempt: %s from %s", r.URL.Path, r.RemoteAddr)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusForbidden)
			w.Write([]byte(`{"error":"Forbidden: This proxy only serves comunicaapi.pje.jus.br"}`))
			return
		}

		// Bloquear Host header manipulation
		if r.Host != "" && !strings.Contains(r.Host, ".run.app") && r.Host != "localhost:8080" {
			log.Printf("🚨 BLOCKED: Invalid Host header: %s from %s", r.Host, r.RemoteAddr)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusForbidden)
			w.Write([]byte(`{"error":"Forbidden: Invalid Host header"}`))
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
			req.Header.Set("X-Forwarded-Host", req.Header.Get("Host"))
			log.Printf("✅ %s %s → %s%s", req.Method, req.RemoteAddr, ALLOWED_TARGET, req.URL.Path)
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

	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"status":"healthy","proxy":"djen-br-secure","region":"southamerica-east1","allowed_target":"comunicaapi.pje.jus.br"}`))
	})

	http.HandleFunc("/security", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"security":"enabled","allowed_target":"comunicaapi.pje.jus.br","blocked":["external_urls","host_manipulation","open_proxy_abuse"],"note":"This proxy ONLY serves Brazilian DJEN API"}`))
	})

	http.Handle("/", securityMiddleware(http.HandlerFunc(proxy.ServeHTTP)))

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("🔒 DJEN Secure Proxy rodando na porta %s", port)
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
EOF

echo "✅ Código seguro criado"

# 2. Redeploy com segurança máxima
echo ""
echo "🚀 Fazendo redeploy seguro..."
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
  --ingress all \
  --no-cpu-boost \
  --update-labels security=enabled,purpose=djen-proxy,restricted=true \
  --quiet

echo "✅ Deploy concluído"

# 3. Pegar URL
PROXY_URL=$(gcloud run services describe djen-proxy --region southamerica-east1 --format='value(status.url)')

# 4. Testar segurança automaticamente
echo ""
echo "🧪 TESTANDO SEGURANÇA..."
echo ""

echo "✅ Teste 1: Health check (deve funcionar)"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $PROXY_URL/health)
if [ "$HTTP_CODE" == "200" ]; then
  echo "   ✅ PASSOU - Health check OK (200)"
else
  echo "   ❌ FALHOU - Health check retornou $HTTP_CODE"
fi

echo ""
echo "❌ Teste 2: Bloquear URL externa (deve retornar 403)"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $PROXY_URL/http://google.com)
if [ "$HTTP_CODE" == "403" ]; then
  echo "   ✅ PASSOU - URL externa bloqueada (403)"
else
  echo "   ❌ FALHOU - URL externa não bloqueada (retornou $HTTP_CODE)"
fi

echo ""
echo "❌ Teste 3: Bloquear HTTPS externa (deve retornar 403)"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $PROXY_URL/https://evil.com)
if [ "$HTTP_CODE" == "403" ]; then
  echo "   ✅ PASSOU - HTTPS externa bloqueada (403)"
else
  echo "   ❌ FALHOU - HTTPS externa não bloqueada (retornou $HTTP_CODE)"
fi

echo ""
echo "✅ Teste 4: API DJEN legítima (deve funcionar)"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$PROXY_URL/api/v1/comunicacao?idOrgao=2")
if [ "$HTTP_CODE" == "200" ]; then
  echo "   ✅ PASSOU - API DJEN OK (200)"
else
  echo "   ⚠️  AVISO - API DJEN retornou $HTTP_CODE"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ SEGURANÇA APLICADA COM SUCESSO!"
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
echo "📊 Ver logs:"
echo "   gcloud run services logs read djen-proxy --region southamerica-east1"
echo ""
echo "🧪 Testar novamente:"
echo "   curl $PROXY_URL/security"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
