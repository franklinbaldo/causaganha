package main
import ("fmt";"log";"net/http";"net/http/httputil";"net/url";"os";"strings";"time")
const TARGET = "https://comunicaapi.pje.jus.br"

// WHITELIST is the only path prefix this proxy forwards to the DJEN
// backend. web/src/lib/djenClient.ts documents that all 7 generated spec
// endpoints (openapi/djen.yml) live under /api/v1/ — /swagger/, bare
// /comunicacao and /login are unused by any caller in this repo (TM-02,
// issue #1609) and are dropped rather than kept "just in case".
var WHITELIST = []string{"/api/"}

// ALLOWED_METHODS is the only HTTP method this proxy forwards. Both
// src/djen_backup/djen.py and web/src/lib/djenClient.ts only ever issue GET
// requests against this proxy; there is no product path that needs the
// backend's mutating methods reachable through it.
var ALLOWED_METHODS = map[string]bool{http.MethodGet: true}

func allowed(path string) bool {
	if path == "/" || path == "/health" || path == "/security" { return true }
	for _, p := range WHITELIST { if strings.HasPrefix(path, p) { return true } }
	return false
}
func security(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !ALLOWED_METHODS[r.Method] {
			log.Printf("🚨 BLOCKED METHOD: %s %s", r.Method, r.URL.Path)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(405)
			w.Write([]byte(fmt.Sprintf(`{"error":"method not allowed","method":"%s"}`, r.Method)))
			return
		}
		if !allowed(r.URL.Path) {
			log.Printf("🚨 BLOCKED: %s", r.URL.Path)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(403)
			w.Write([]byte(fmt.Sprintf(`{"error":"forbidden","path":"%s"}`, r.URL.Path)))
			return
		}
		log.Printf("✅ ALLOWED: %s", r.URL.Path)
		next.ServeHTTP(w, r)
	})
}
func main() {
	target, _ := url.Parse(TARGET)
	proxy := &httputil.ReverseProxy{Director: func(r *http.Request) { r.URL.Scheme = target.Scheme; r.URL.Host = target.Host; r.Host = target.Host }, Transport: &http.Transport{MaxIdleConns: 100, IdleConnTimeout: 90 * time.Second}}
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) })
	http.HandleFunc("/security", func(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"whitelist":["/api/"],"methods":["GET"]}`)) })
	http.Handle("/", security(http.HandlerFunc(proxy.ServeHTTP)))
	port := os.Getenv("PORT"); if port == "" { port = "8080" }
	log.Printf("🔒 Proxy: %s", port)
	http.ListenAndServe(":"+port, nil)
}
