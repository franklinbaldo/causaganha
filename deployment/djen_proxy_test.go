package main

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

// TM-02 (docs/SECURITY_THREAT_MODEL.md, issue #1609): djen_proxy.go fronts
// the real comunicaapi.pje.jus.br backend with no authentication. Its
// security boundary is path/method allowlisting alone, so it must reject
// everything the product doesn't actually need.

func TestAllowed(t *testing.T) {
	cases := map[string]bool{
		"/":                                  true,
		"/api/v1/comunicacao":                true,
		"/api/v1/caderno/TJRO/2026-01-01/D":  true,
		"/api/v1/comunicacao/tribunal":       true,
		"/swagger/index.html":                false,
		"/comunicacao":                       false,
		"/login":                             false,
		"/evil":                              false,
		"/api-look-alike/v1/comunicacao":     false,
	}
	for path, want := range cases {
		if got := allowed(path); got != want {
			t.Errorf("allowed(%q) = %v, want %v", path, got, want)
		}
	}
}

func TestSecurityRejectsMutatingMethods(t *testing.T) {
	inner := http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
	})
	handler := security(inner)

	for _, method := range []string{http.MethodPost, http.MethodPut, http.MethodDelete, http.MethodPatch, http.MethodOptions} {
		req := httptest.NewRequest(method, "/api/v1/comunicacao", nil)
		rr := httptest.NewRecorder()
		handler.ServeHTTP(rr, req)
		if rr.Code != http.StatusMethodNotAllowed {
			t.Errorf("method %s on whitelisted path: got status %d, want %d", method, rr.Code, http.StatusMethodNotAllowed)
		}
	}
}

func TestSecurityAllowsGetOnWhitelistedPath(t *testing.T) {
	called := false
	inner := http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		called = true
		w.WriteHeader(http.StatusOK)
	})
	handler := security(inner)

	req := httptest.NewRequest(http.MethodGet, "/api/v1/comunicacao", nil)
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)

	if rr.Code != http.StatusOK || !called {
		t.Errorf("GET on whitelisted path: got status=%d called=%v, want 200/true", rr.Code, called)
	}
}

func TestSecurityRejectsGetOnLoginSwaggerAndBareComunicacao(t *testing.T) {
	inner := http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
	})
	handler := security(inner)

	for _, path := range []string{"/login", "/swagger/index.html", "/comunicacao"} {
		req := httptest.NewRequest(http.MethodGet, path, nil)
		rr := httptest.NewRecorder()
		handler.ServeHTTP(rr, req)
		if rr.Code != http.StatusForbidden {
			t.Errorf("GET %s: got status %d, want %d", path, rr.Code, http.StatusForbidden)
		}
	}
}

func TestSecurityRejectsMutatingMethodEvenOffWhitelist(t *testing.T) {
	// A rejected method must never leak whether the path would otherwise be
	// allowlisted — both checks must independently fail closed.
	inner := http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
	})
	handler := security(inner)

	req := httptest.NewRequest(http.MethodPost, "/login", nil)
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)
	if rr.Code != http.StatusMethodNotAllowed {
		t.Errorf("POST /login: got status %d, want %d", rr.Code, http.StatusMethodNotAllowed)
	}
}

func TestArchiveDownloadPathAllowlist(t *testing.T) {
	cases := map[string]bool{
		"/download/djen-tjro-2026/comunicacoes.parquet":          true,
		"/download/datajud-tjro/processos.parquet":               true,
		"/download/causaganha-dashboard/indice_processual.parquet": true,
		"/download/evil-item/comunicacoes.parquet":               false,
		"/download/djen-tjro-2026/secret.txt":                    false,
		"/download/djen-tjro-2026/../etc/passwd.parquet":         false,
	}
	for path, want := range cases {
		if got := isArchiveDownloadPath(path); got != want {
			t.Errorf("isArchiveDownloadPath(%q) = %v, want %v", path, got, want)
		}
	}
}

func TestArchiveDownloadOptionsAndInvalidPaths(t *testing.T) {
	inner := http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
	})
	handler := security(inner)

	optReq := httptest.NewRequest(http.MethodOptions, "/download/djen-tjro-2026/comunicacoes.parquet", nil)
	optRR := httptest.NewRecorder()
	handler.ServeHTTP(optRR, optReq)
	if optRR.Code != http.StatusNoContent {
		t.Errorf("OPTIONS /download/...: got %d, want 204", optRR.Code)
	}
	if got := optRR.Header().Get("Access-Control-Allow-Origin"); got != "*" {
		t.Errorf("Access-Control-Allow-Origin = %q, want *", got)
	}

	badReq := httptest.NewRequest(http.MethodGet, "/download/evil-item/file.txt", nil)
	badRR := httptest.NewRecorder()
	handler.ServeHTTP(badRR, badReq)
	if badRR.Code != http.StatusNotFound {
		t.Errorf("GET invalid download path: got %d, want 404", badRR.Code)
	}
}
