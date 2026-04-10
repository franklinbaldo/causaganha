package main
import ("fmt";"log";"net/http";"net/http/httputil";"net/url";"os";"strings";"time")
const TARGET = "https://comunicaapi.pje.jus.br"
var WHITELIST = []string{"/api/", "/swagger/", "/comunicacao", "/login"}
func allowed(path string) bool {
	if path == "/" || path == "/health" || path == "/security" { return true }
	for _, p := range WHITELIST { if strings.HasPrefix(path, p) { return true } }
	return false
}
func security(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
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
	http.HandleFunc("/security", func(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"whitelist":["/api/","/swagger/","/comunicacao","/login"]}`)) })
	http.Handle("/", security(http.HandlerFunc(proxy.ServeHTTP)))
	port := os.Getenv("PORT"); if port == "" { port = "8080" }
	log.Printf("🔒 Proxy: %s", port)
	http.ListenAndServe(":"+port, nil)
}
