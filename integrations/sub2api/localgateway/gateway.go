// Package localgateway is a capability router for explicitly configured Sub2API LMA groups.
// It performs no inference. Every upstream is a private/loopback Android API listener.
package localgateway

import (
	"bufio"
	"bytes"
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"
)

type Object = map[string]any
type Account struct {
	ID       int64             `json:"account_id"`
	GroupID  int64             `json:"group_id"`
	BaseURL  string            `json:"base_url"`
	KeyEnv   string            `json:"key_env"`
	Instance string            `json:"expected_instance_id,omitempty"`
	Aliases  map[string]string `json:"aliases,omitempty"`
}
type Config struct {
	StateFile string    `json:"state_file"`
	Accounts  []Account `json:"accounts"`
}
type Principal struct {
	Owner   string
	GroupID int64
	Allows  func(string) bool
}
type Binding struct {
	Owner     string `json:"owner"`
	AccountID int64  `json:"account_id"`
	Instance  string `json:"instance"`
	Model     string `json:"model"`
	Kind      string `json:"kind"`
	Remote    string `json:"remote"`
}
type Intent struct {
	Owner     string          `json:"owner"`
	Endpoint  string          `json:"endpoint"`
	Hash      string          `json:"hash"`
	Model     string          `json:"model"`
	AccountID int64           `json:"account_id"`
	Instance  string          `json:"instance"`
	Body      json.RawMessage `json:"body"`
	Created   int64           `json:"created"`
	Remote    string          `json:"remote,omitempty"`
	Finished  int64           `json:"finished,omitempty"`
}
type Registry struct {
	Instance    string   `json:"instance"`
	ETag        string   `json:"etag"`
	Updated     int64    `json:"updated"`
	LastSuccess int64    `json:"last_success"`
	Models      []Object `json:"models"`
}
type durable struct {
	Schema     string             `json:"schema"`
	Bindings   map[string]Binding `json:"bindings"`
	Intents    map[string]Intent  `json:"intents"`
	Registries map[int64]Registry `json:"registries"`
}
type Gateway struct {
	mu           sync.Mutex
	cfg          Config
	state        durable
	accounts     map[int64]Account
	client       *http.Client
	textClient   *http.Client
	closed       chan struct{}
	done         sync.WaitGroup
	eventCache   map[int64]*phoneEvents
	eventClients chan struct{}
}

func New(cfg Config) (*Gateway, error) {
	if cfg.StateFile == "" || len(cfg.Accounts) == 0 {
		return nil, errors.New("LMA requires an explicit state file and phone accounts")
	}
	if len(cfg.Accounts) > 32 {
		return nil, errors.New("At most 32 explicit phone accounts are allowed")
	}
	g := &Gateway{cfg: cfg, accounts: map[int64]Account{}, closed: make(chan struct{}), eventCache: map[int64]*phoneEvents{}, eventClients: make(chan struct{}, 64)}
	g.state = durable{Schema: "lma.sub2api/1", Bindings: map[string]Binding{}, Intents: map[string]Intent{}, Registries: map[int64]Registry{}}
	data, err := os.ReadFile(cfg.StateFile)
	if err == nil {
		if json.Unmarshal(data, &g.state) != nil || g.state.Schema != "lma.sub2api/1" {
			return nil, errors.New("Invalid LMA durable registry")
		}
	} else if !os.IsNotExist(err) {
		return nil, errors.New("Cannot read LMA registry")
	}
	if g.state.Bindings == nil || g.state.Intents == nil || g.state.Registries == nil {
		return nil, errors.New("Incomplete LMA registry")
	}
	for _, a := range cfg.Accounts {
		u, e := url.Parse(a.BaseURL)
		if e != nil || u.User != nil || u.RawQuery != "" || u.Fragment != "" || u.Path != "" && u.Path != "/" || u.Scheme != "http" && u.Scheme != "https" {
			return nil, errors.New("Use a phone API origin without credentials, query or path")
		}
		if a.ID < 1 || a.GroupID < 1 || a.KeyEnv == "" || os.Getenv(a.KeyEnv) == "" {
			return nil, errors.New("LMA account identity or environment credential is missing")
		}
		if _, ok := g.accounts[a.ID]; ok {
			return nil, errors.New("Duplicate LMA account identity")
		}
		a.BaseURL = strings.TrimSuffix(a.BaseURL, "/")
		g.accounts[a.ID] = a
	}
	transport := &http.Transport{Proxy: nil, MaxIdleConnsPerHost: 6, ResponseHeaderTimeout: 130 * time.Second, IdleConnTimeout: 60 * time.Second,
		DialContext: func(ctx context.Context, network, address string) (net.Conn, error) {
			host, port, e := net.SplitHostPort(address)
			if e != nil {
				return nil, e
			}
			ips, e := net.DefaultResolver.LookupIPAddr(ctx, host)
			if e != nil {
				return nil, e
			}
			for _, ip := range ips {
				if !ip.IP.IsLoopback() && !ip.IP.IsPrivate() {
					return nil, errors.New("LMA phone origins must resolve exclusively to local/private addresses")
				}
			}
			if len(ips) == 0 {
				return nil, errors.New("No local phone address")
			}
			return (&net.Dialer{Timeout: 3 * time.Second}).DialContext(ctx, network, net.JoinHostPort(ips[0].IP.String(), port))
		}}
	g.client = &http.Client{Transport: transport, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}
	// Text prefill/loading can exceed the ordinary HTTP header wait.
	textTransport := transport.Clone()
	textTransport.ResponseHeaderTimeout = 0
	textClient := *g.client
	textClient.Transport = textTransport
	g.textClient = &textClient
	return g, nil
}
func FromEnvironment() (*Gateway, error) {
	p := os.Getenv("SUB2API_LMA_CONFIG")
	if p == "" {
		return nil, nil
	}
	b, e := os.ReadFile(p)
	if e != nil {
		return nil, errors.New("Cannot read explicit LMA configuration")
	}
	var c Config
	d := json.NewDecoder(bytes.NewReader(b))
	d.DisallowUnknownFields()
	if d.Decode(&c) != nil {
		return nil, errors.New("Invalid LMA configuration")
	}
	g, e := New(c)
	if e == nil {
		g.Start()
	}
	return g, e
}
func (g *Gateway) Configured(group int64) bool {
	for _, a := range g.accounts {
		if a.GroupID == group {
			return true
		}
	}
	return false
}
func (g *Gateway) saveLocked() error {
	b, e := json.Marshal(g.state)
	if e != nil {
		return e
	}
	if len(b) > 64<<20 {
		return errors.New("LMA registry capacity exhausted")
	}
	if e = os.MkdirAll(filepath.Dir(g.cfg.StateFile), 0700); e != nil {
		return e
	}
	f, e := os.CreateTemp(filepath.Dir(g.cfg.StateFile), ".lma-atomic-*")
	if e != nil {
		return e
	}
	p := f.Name()
	defer os.Remove(p)
	if e = f.Chmod(0600); e == nil {
		_, e = f.Write(b)
	}
	if e == nil {
		e = f.Sync()
	}
	ce := f.Close()
	if e == nil {
		e = ce
	}
	if e != nil {
		return e
	}
	return replaceFile(p, g.cfg.StateFile)
}
func (g *Gateway) Start() {
	for id := range g.accounts {
		g.done.Add(1)
		go func(id int64) {
			defer g.done.Done()
			delay := time.Duration(0)
			backoff := 30 * time.Second
			for {
				timer := time.NewTimer(delay)
				select {
				case <-g.closed:
					timer.Stop()
					return
				case <-timer.C:
				}
				e := g.Sync(context.Background(), id)
				if e != nil {
					delay = backoff
					backoff *= 2
					if backoff > 300*time.Second {
						backoff = 300 * time.Second
					}
				} else {
					backoff = 30 * time.Second
					var b [1]byte
					rand.Read(b[:])
					delay = time.Duration(24000+int(b[0])*12000/255) * time.Millisecond
				}
			}
		}(id)
	}
}
func (g *Gateway) Close() {
	close(g.closed)
	g.done.Wait()
	g.client.CloseIdleConnections()
	g.textClient.CloseIdleConnections()
}
func (g *Gateway) Sync(ctx context.Context, id int64) error {
	a, ok := g.accounts[id]
	if !ok {
		return errors.New("Unknown account")
	}
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	req, _ := http.NewRequestWithContext(ctx, "GET", a.BaseURL+"/v1/models", nil)
	req.Header.Set("Authorization", "Bearer "+os.Getenv(a.KeyEnv))
	g.mu.Lock()
	old := g.state.Registries[id]
	g.mu.Unlock()
	if old.ETag != "" {
		req.Header.Set("If-None-Match", old.ETag)
	}
	r, e := g.client.Do(req)
	if e != nil {
		return errors.New("LMA phone catalogue is unreachable")
	}
	defer r.Body.Close()
	now := time.Now().UnixMilli()
	if r.StatusCode == 304 && old.Instance != "" {
		g.mu.Lock()
		defer g.mu.Unlock()
		names, err := publishedNames(a, old.Models)
		if err != nil {
			return err
		}
		for other, account := range g.accounts {
			if other != id && account.GroupID == a.GroupID {
				occupied, err := publishedNames(account, g.state.Registries[other].Models)
				if err != nil {
					return err
				}
				for name := range names {
					if occupied[name] != "" {
						return errors.New("Local model/alias conflict")
					}
				}
			}
		}
		old.LastSuccess = now
		g.state.Registries[id] = old
		return g.saveLocked()
	}
	if r.StatusCode != 200 {
		return errors.New("LMA phone catalogue was rejected")
	}
	b, e := io.ReadAll(io.LimitReader(r.Body, 4<<20+1))
	if e != nil || len(b) > 4<<20 {
		return errors.New("Invalid catalogue size")
	}
	var doc struct {
		Object string   `json:"object"`
		Data   []Object `json:"data"`
		Meta   struct {
			Schema   string `json:"schema"`
			Instance string `json:"instance_id"`
		} `json:"x_lma"`
	}
	if json.Unmarshal(b, &doc) != nil || doc.Object != "list" || doc.Meta.Schema != "lma.catalogue/1" || doc.Meta.Instance == "" {
		return errors.New("Not an LMA catalogue")
	}
	if a.Instance != "" && a.Instance != doc.Meta.Instance || old.Instance != "" && old.Instance != doc.Meta.Instance {
		return errors.New("Phone instance changed; explicit administrator reconfiguration is required")
	}
	seen := map[string]bool{}
	for _, m := range doc.Data {
		mid, _ := m["id"].(string)
		x := object(m["x_lma"])
		publication := object(x["publication"])
		if !validID.MatchString(mid) || seen[mid] || publication["eligible"] != true || len(array(x["operations"])) == 0 {
			return errors.New("Invalid published model")
		}
		seen[mid] = true
	}
	g.mu.Lock()
	defer g.mu.Unlock()
	names, err := publishedNames(a, doc.Data)
	if err != nil {
		return err
	}
	for other, account := range g.accounts {
		if other != id && account.GroupID == a.GroupID {
			occupied, err := publishedNames(account, g.state.Registries[other].Models)
			if err != nil {
				return err
			}
			for name := range names {
				if occupied[name] != "" {
					return errors.New("Local model/alias conflict in this group; use a distinct group")
				}
			}
		}
	}
	g.state.Registries[id] = Registry{Instance: doc.Meta.Instance, ETag: r.Header.Get("ETag"), Updated: now, LastSuccess: now, Models: doc.Data}
	return g.saveLocked()
}

var validID = regexp.MustCompile(`^[A-Za-z0-9_-]{1,128}$`)

func object(v any) Object {
	m, _ := v.(map[string]any)
	if m == nil {
		return Object{}
	}
	return m
}
func array(v any) []any                  { a, _ := v.([]any); return a }
func str(v any) string                   { s, _ := v.(string); return s }
func digest(v []byte) string             { h := sha256.Sum256(v); return hex.EncodeToString(h[:]) }
func clone(o Object) Object              { b, _ := json.Marshal(o); var r Object; json.Unmarshal(b, &r); return r }
func allowed(p Principal, m string) bool { return p.Allows == nil || p.Allows(m) }
func fail(w http.ResponseWriter, status int, code string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(Object{"error": Object{"type": "lma_gateway_error", "param": nil, "code": code, "message": strings.ReplaceAll(code, "_", " ")}})
}

type choice struct {
	account  Account
	registry Registry
	model    Object
	public   string
	remote   string
}

func (g *Gateway) choicesLocked(p Principal) []choice {
	var out []choice
	for id, a := range g.accounts {
		if a.GroupID != p.GroupID {
			continue
		}
		r := g.state.Registries[id]
		for _, m := range r.Models {
			mid := str(m["id"])
			if allowed(p, mid) {
				out = append(out, choice{a, r, m, mid, mid})
			}
			for alias, target := range a.Aliases {
				if target == mid && validID.MatchString(alias) && allowed(p, alias) {
					out = append(out, choice{a, r, m, alias, mid})
				}
			}
		}
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].public == out[j].public {
			return out[i].account.ID < out[j].account.ID
		}
		return out[i].public < out[j].public
	})
	return out
}
func current(r Registry) bool {
	return r.Instance != "" && time.Now().UnixMilli()-r.LastSuccess <= 90000
}
func (g *Gateway) catalogue(p Principal) (Object, error) {
	g.mu.Lock()
	defer g.mu.Unlock()
	choices := g.choicesLocked(p)
	seen := map[string]bool{}
	out := []any{}
	ever := false
	for id, a := range g.accounts {
		if a.GroupID == p.GroupID && g.state.Registries[id].Instance != "" {
			ever = true
		}
	}
	if !ever {
		return nil, errors.New("First phone catalogue is unavailable")
	}
	for _, c := range choices {
		if seen[c.public] {
			continue
		}
		seen[c.public] = true
		m := clone(c.model)
		m["id"] = c.public
		x := object(m["x_lma"])
		ready := object(x["ready"])
		if !current(c.registry) {
			ready["available"] = false
			ready["status"] = "offline"
			ready["reason_codes"] = []string{"catalogue_stale"}
		}
		x["ready"] = ready
		m["x_lma"] = x
		out = append(out, m)
	}
	return Object{"object": "list", "data": out, "x_lma": Object{"schema": "lma.gateway-catalogue/1", "scope": "authenticated_group", "no_cloud_fallback": true}}, nil
}
func (g *Gateway) selectLocked(p Principal, model, operation string) (choice, error) {
	for _, c := range g.choicesLocked(p) {
		if c.public != model || !current(c.registry) {
			continue
		}
		for _, op := range array(object(c.model["x_lma"])["operations"]) {
			if op == operation {
				return c, nil
			}
		}
	}
	return choice{}, errors.New("No current phone supports the selected operation")
}
func (g *Gateway) bindingLocked(p Principal, id, kind string) (Binding, bool) {
	b, ok := g.state.Bindings[id]
	if !ok || b.Owner != p.Owner || b.Kind != kind || !allowed(p, b.Model) {
		return Binding{}, false
	}
	a, ok := g.accounts[b.AccountID]
	return b, ok && a.GroupID == p.GroupID
}
func (g *Gateway) bindLocked(p Principal, c choice, kind, remote string) (string, error) {
	if !validID.MatchString(remote) {
		return "", errors.New("Invalid upstream identity")
	}
	for id, b := range g.state.Bindings {
		if b.Owner == p.Owner && b.AccountID == c.account.ID && b.Instance == c.registry.Instance && b.Kind == kind && b.Remote == remote {
			return id, nil
		}
	}
	if len(g.state.Bindings) >= 16384 {
		return "", errors.New("Binding retention is full")
	}
	var b [16]byte
	if _, e := rand.Read(b[:]); e != nil {
		return "", e
	}
	id := "lma_" + kind + "_" + hex.EncodeToString(b[:])
	g.state.Bindings[id] = Binding{p.Owner, c.account.ID, c.registry.Instance, c.public, kind, remote}
	return id, nil
}
func (g *Gateway) rewriteLocked(p Principal, c choice, o Object) error {
	kind := ""
	switch str(o["object"]) {
	case "lma.job":
		kind = "job"
	case "lma.artifact":
		kind = "artifact"
	case "lma.upload":
		kind = "upload"
	}
	if kind != "" {
		id, e := g.bindLocked(p, c, kind, str(o["id"]))
		if e != nil {
			return e
		}
		o["id"] = id
		if kind == "job" {
			o["model"] = c.public
		}
		if kind == "artifact" {
			o["content_path"] = "/v1/lma/artifacts/" + id + "/content"
		}
	}
	if x, ok := o["x_lma"].(map[string]any); ok && str(x["job_id"]) != "" {
		id, e := g.bindLocked(p, c, "job", str(x["job_id"]))
		if e != nil {
			return e
		}
		x["job_id"] = id
	}
	if str(o["artifact_id"]) != "" {
		id, e := g.bindLocked(p, c, "artifact", str(o["artifact_id"]))
		if e != nil {
			return e
		}
		o["artifact_id"] = id
	}
	for _, v := range array(o["events"]) {
		event := object(v)
		if remote := str(event["jobId"]); remote != "" {
			id, e := g.bindLocked(p, c, "job", remote)
			if e != nil {
				return e
			}
			event["jobId"] = id
		}
	}
	for _, key := range []string{"outputs", "data"} {
		for _, v := range array(o[key]) {
			if m, ok := v.(map[string]any); ok {
				if e := g.rewriteLocked(p, c, m); e != nil {
					return e
				}
			}
		}
	}
	return nil
}
func (g *Gateway) inputsLocked(p Principal, c choice, body Object) error {
	input := object(body["input"])
	if lma, ok := body["lma"].(map[string]any); ok {
		input = lma
	}
	for _, v := range array(input["artifacts"]) {
		ref := object(v)
		b, ok := g.bindingLocked(p, str(ref["artifactId"]), "artifact")
		if !ok || b.AccountID != c.account.ID || b.Instance != c.registry.Instance {
			return errors.New("The selected input is not owned on this phone")
		}
		ref["artifactId"] = b.Remote
	}
	for _, v := range array(body["adapters"]) {
		a := object(v)
		mid := str(a["model"])
		// LoRA components deliberately do not masquerade as generation models.
		// The phone validates complete local assets, architecture and base compatibility.
		if !validID.MatchString(mid) || !allowed(p, mid) {
			return errors.New("Adapter is not available on the bound phone")
		}
		if target, ok := c.account.Aliases[mid]; ok {
			a["model"] = target
		}
	}
	if options, ok := body["lma"].(map[string]any); ok && options["adapters"] != nil {
		return g.inputsLocked(p, c, Object{"adapters": options["adapters"]})
	}
	return nil
}

var forwarded = []string{"Content-Type", "Accept", "Range", "If-Range", "If-None-Match", "Last-Event-ID", "Upload-Offset"}
var returned = []string{"Content-Type", "Content-Length", "Content-Range", "Accept-Ranges", "ETag", "Retry-After", "X-Audio-Format", "X-Accel-Buffering", "Cache-Control"}

// Parent-phone lists are filtered against durable owner bindings before any bytes reach a caller.
func (g *Gateway) listOwned(w http.ResponseWriter, r *http.Request, p Principal, kind string) {
	if r.Method != "GET" && r.Method != "HEAD" {
		fail(w, 405, "lma_method_not_allowed")
		return
	}
	if r.ContentLength > 0 {
		fail(w, 400, "lma_unexpected_body")
		return
	}
	result := []any{}
	for id, a := range g.accounts {
		if a.GroupID != p.GroupID {
			continue
		}
		g.mu.Lock()
		reg := g.state.Registries[id]
		g.mu.Unlock()
		if !current(reg) {
			fail(w, 503, "lma_bound_phone_unavailable")
			return
		}
		ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
		req, _ := http.NewRequestWithContext(ctx, "GET", a.BaseURL+"/v1/lma/"+kind+"s", nil)
		req.Header.Set("Authorization", "Bearer "+os.Getenv(a.KeyEnv))
		response, e := g.client.Do(req)
		if e != nil {
			cancel()
			fail(w, 503, "lma_bound_phone_unavailable")
			return
		}
		b, e := io.ReadAll(io.LimitReader(response.Body, 4<<20+1))
		response.Body.Close()
		cancel()
		var doc Object
		if e != nil || response.StatusCode != 200 || len(b) > 4<<20 || json.Unmarshal(b, &doc) != nil {
			fail(w, 502, "lma_invalid_upstream_body")
			return
		}
		g.mu.Lock()
		for _, value := range array(doc["data"]) {
			item := object(value)
			remote := str(item["id"])
			for _, binding := range g.state.Bindings {
				if binding.Owner == p.Owner && binding.AccountID == id && binding.Instance == reg.Instance && binding.Kind == kind && binding.Remote == remote && allowed(p, binding.Model) {
					c := choice{account: a, registry: reg, public: binding.Model}
					if e = g.rewriteLocked(p, c, item); e == nil {
						result = append(result, item)
					}
					break
				}
			}
		}
		if e == nil {
			e = g.saveLocked()
		}
		g.mu.Unlock()
		if e != nil {
			fail(w, 503, "lma_durable_state_unavailable")
			return
		}
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(200)
	if r.Method != "HEAD" {
		json.NewEncoder(w).Encode(Object{"object": "list", "data": result})
	}
}

func (g *Gateway) ServeHTTP(w http.ResponseWriter, r *http.Request, p Principal) {
	if p.Owner == "" || !g.Configured(p.GroupID) {
		fail(w, 403, "lma_group_unavailable")
		return
	}
	if r.Header.Get("Origin") != "" {
		fail(w, 403, "lma_browser_origin_rejected")
		return
	}
	path := r.URL.Path
	if strings.Contains(path, "..") || strings.Contains(path, "\\") || r.URL.RawPath != "" {
		fail(w, 400, "lma_invalid_path")
		return
	}
	for _, kind := range []string{"job", "upload", "artifact"} {
		if path == "/v1/lma/"+kind+"s" && (r.Method == "GET" || r.Method == "HEAD") {
			g.listOwned(w, r, p, kind)
			return
		}
	}
	if path == "/v1/models" || strings.HasPrefix(path, "/v1/models/") || path == "/v1/capabilities" || path == "/v1/lma/capabilities" {
		if r.Method != "GET" && r.Method != "HEAD" {
			fail(w, 405, "lma_method_not_allowed")
			return
		}
		doc, e := g.catalogue(p)
		if e != nil {
			fail(w, 503, "lma_catalogue_unavailable")
			return
		}
		if strings.HasPrefix(path, "/v1/models/") {
			id := strings.TrimPrefix(path, "/v1/models/")
			found := false
			for _, v := range array(doc["data"]) {
				m := object(v)
				if m["id"] == id {
					doc = m
					found = true
					break
				}
			}
			if !found {
				fail(w, 404, "lma_model_unavailable")
				return
			}
		}
		if strings.HasSuffix(path, "capabilities") {
			doc = Object{"schema": "lma.gateway-capabilities/1", "execution": "same_android_phone", "models": doc["data"], "profiles": []string{"openai_subset", "lma_extension"}}
		}
		b, _ := json.Marshal(doc)
		tag := "\"" + digest(b) + "\""
		w.Header().Set("ETag", tag)
		w.Header().Set("Cache-Control", "private, no-cache")
		w.Header().Set("Content-Type", "application/json")
		if r.Header.Get("If-None-Match") == tag {
			w.WriteHeader(304)
			return
		}
		w.WriteHeader(200)
		if r.Method != "HEAD" {
			w.Write(b)
		}
		return
	}
	if r.ContentLength > 256<<10 {
		fail(w, 413, "lma_body_too_large")
		return
	}
	payload, e := io.ReadAll(io.LimitReader(r.Body, 256<<10+1))
	if e != nil || len(payload) > 256<<10 {
		fail(w, 413, "lma_body_too_large")
		return
	}
	var body Object
	if len(payload) > 0 && strings.HasPrefix(r.Header.Get("Content-Type"), "application/json") {
		if json.Unmarshal(payload, &body) != nil {
			fail(w, 400, "lma_invalid_json")
			return
		}
	}
	operation := ""
	creation := r.Method == "POST" && (path == "/v1/images/generations" || path == "/v1/audio/speech" || path == "/v1/lma/jobs" || path == "/v1/chat/completions" || path == "/v1/completions")
	upload := r.Method == "POST" && path == "/v1/lma/uploads"
	preflight := r.Method == "POST" && path == "/v1/lma/jobs/preflight"
	switch path {
	case "/v1/images/generations":
		operation = "image.generate"
	case "/v1/audio/speech":
		operation = "speech.synthesize"
	case "/v1/chat/completions", "/v1/completions":
		operation = "text.generate"
	case "/v1/lma/jobs", "/v1/lma/jobs/preflight":
		operation = str(body["type"])
	}
	key := r.Header.Get("Idempotency-Key")
	namespace := ""
	var c choice
	g.mu.Lock()
	unlockFail := func(status int, code string) { g.mu.Unlock(); fail(w, status, code) }
	if creation && operation != "text.generate" {
		if len(key) < 1 || len(key) > 160 || strings.IndexFunc(key, func(c rune) bool { return c < 33 || c > 126 }) >= 0 {
			unlockFail(400, "lma_idempotency_key_required")
			return
		}
		namespace = digest([]byte(p.Owner + "\x00" + path + "\x00" + key))
		canonical, _ := json.Marshal(body)
		hash := digest(canonical)
		if intent, ok := g.state.Intents[namespace]; ok {
			if hash != intent.Hash {
				unlockFail(409, "lma_idempotency_conflict")
				return
			}
			a, ok := g.accounts[intent.AccountID]
			if !ok || a.GroupID != p.GroupID || !allowed(p, intent.Model) {
				unlockFail(404, "lma_bound_account_unavailable")
				return
			}
			reg := g.state.Registries[a.ID]
			if reg.Instance != intent.Instance || !current(reg) {
				unlockFail(503, "lma_bound_phone_unavailable")
				return
			}
			c = choice{account: a, registry: reg, public: intent.Model}
			payload = append([]byte{}, intent.Body...)
		} else {
			c, e = g.selectLocked(p, str(body["model"]), operation)
			if e != nil {
				unlockFail(503, "lma_model_unavailable")
				return
			}
			if g.inputsLocked(p, c, body) != nil {
				unlockFail(404, "lma_input_unavailable")
				return
			}
			body["model"] = c.remote
			saved := object(object(c.model["x_lma"])["saved_parameters"])
			params := object(body["parameters"])
			if path != "/v1/lma/jobs" {
				local := object(body["lma"])
				params = object(local["parameters"])
				for k, v := range saved {
					if _, ok := params[k]; !ok {
						params[k] = v
					}
				}
				local["parameters"] = params
				body["lma"] = local
			} else {
				for k, v := range saved {
					if _, ok := params[k]; !ok {
						params[k] = v
					}
				}
				body["parameters"] = params
			}
			payload, _ = json.Marshal(body)
			now := time.Now().UnixMilli()
			for k, v := range g.state.Intents {
				if v.Finished > 0 && now-v.Finished >= 86400000 {
					delete(g.state.Intents, k)
				}
			}
			if len(g.state.Intents) >= 4096 {
				unlockFail(503, "lma_retention_capacity")
				return
			}
			g.state.Intents[namespace] = Intent{Owner: p.Owner, Endpoint: path, Hash: hash, Model: c.public, AccountID: c.account.ID, Instance: c.registry.Instance, Body: append([]byte{}, payload...), Created: now}
			if g.saveLocked() != nil {
				unlockFail(503, "lma_durable_state_unavailable")
				return
			}
		}
	} else if creation || upload || preflight {
		if upload {
			operation = ""
			for _, candidate := range g.choicesLocked(p) {
				if candidate.public == str(body["model"]) && current(candidate.registry) {
					c = candidate
					break
				}
			}
		} else {
			c, e = g.selectLocked(p, str(body["model"]), operation)
		}
		if c.account.ID == 0 || e != nil {
			unlockFail(503, "lma_model_unavailable")
			return
		}
		if g.inputsLocked(p, c, body) != nil {
			unlockFail(404, "lma_input_unavailable")
			return
		}
		body["model"] = c.remote
		payload, _ = json.Marshal(body)
	} else {
		parts := strings.Split(strings.TrimPrefix(path, "/v1/lma/"), "/")
		if len(parts) < 2 || len(parts) > 4 {
			unlockFail(404, "lma_endpoint_unavailable")
			return
		}
		kind := strings.TrimSuffix(parts[0], "s")
		if kind != "job" && kind != "artifact" && kind != "upload" {
			unlockFail(404, "lma_endpoint_unavailable")
			return
		}
		b, ok := g.bindingLocked(p, parts[1], kind)
		if !ok {
			unlockFail(404, "lma_owned_resource_not_found")
			return
		}
		a := g.accounts[b.AccountID]
		reg := g.state.Registries[b.AccountID]
		if !current(reg) || reg.Instance != b.Instance {
			unlockFail(503, "lma_bound_phone_unavailable")
			return
		}
		c = choice{account: a, registry: reg, public: b.Model}
		parts[1] = b.Remote
		path = "/v1/lma/" + strings.Join(parts, "/")
		suffix := ""
		if len(parts) >= 3 {
			suffix = parts[2]
		}
		ok = r.Method == "GET" || r.Method == "HEAD" || r.Method == "DELETE" && suffix == "" || kind == "upload" && r.Method == "PUT" && suffix == "" || r.Method == "POST" && (suffix == "complete" && kind == "upload" || (suffix == "cancel" || suffix == "retry") && kind == "job")
		if !ok || suffix != "" && suffix != "content" && suffix != "events" && suffix != "complete" && suffix != "cancel" && suffix != "retry" && suffix != "audio" || len(parts) == 4 && (suffix != "audio" || kind != "job" || !regexp.MustCompile(`^[0-9]{1,4}$`).MatchString(parts[3])) {
			unlockFail(405, "lma_method_not_allowed")
			return
		}
		if suffix == "retry" {
			if len(key) < 1 || len(key) > 160 || strings.IndexFunc(key, func(c rune) bool { return c < 33 || c > 126 }) >= 0 {
				unlockFail(400, "lma_idempotency_key_required")
				return
			}
			namespace = digest([]byte(p.Owner + "\x00" + r.URL.Path + "\x00" + key))
			hash := digest(payload)
			if old, exists := g.state.Intents[namespace]; exists {
				if old.Hash != hash {
					unlockFail(409, "lma_idempotency_conflict")
					return
				}
			} else {
				if len(g.state.Intents) >= 4096 {
					unlockFail(503, "lma_retention_capacity")
					return
				}
				g.state.Intents[namespace] = Intent{Owner: p.Owner, Endpoint: r.URL.Path, Hash: hash, Model: c.public, AccountID: c.account.ID, Instance: c.registry.Instance, Body: append([]byte{}, payload...), Created: time.Now().UnixMilli()}
				if g.saveLocked() != nil {
					unlockFail(503, "lma_durable_state_unavailable")
					return
				}
			}
		}
	}
	g.mu.Unlock()
	if r.Method == "GET" && strings.HasSuffix(path, "/events") && strings.Contains(r.Header.Get("Accept"), "text/event-stream") {
		parts := strings.Split(strings.Trim(path, "/"), "/")
		g.eventStream(w, r, p, c, parts[len(parts)-2])
		return
	}
	var ctx context.Context
	var cancel context.CancelFunc
	if path == "/v1/chat/completions" || path == "/v1/completions" {
		ctx, cancel = context.WithCancel(r.Context())
	} else {
		ctx, cancel = context.WithTimeout(r.Context(), 135*time.Second)
	}
	defer cancel()
	target := c.account.BaseURL + path
	if r.URL.RawQuery != "" {
		q := r.URL.Query()
		for name := range q {
			if name != "after" {
				fail(w, 400, "lma_unsupported_query")
				return
			}
		}
		target += "?" + q.Encode()
	}
	upstream, e := http.NewRequestWithContext(ctx, r.Method, target, bytes.NewReader(payload))
	if e != nil {
		fail(w, 400, "lma_invalid_route")
		return
	}
	for _, h := range forwarded {
		if v := r.Header.Get(h); v != "" {
			upstream.Header.Set(h, v)
		}
	}
	upstream.Header.Set("Authorization", "Bearer "+os.Getenv(c.account.KeyEnv))
	if namespace != "" {
		upstream.Header.Set("Idempotency-Key", "gw_"+namespace)
	}
	client := g.client
	if path == "/v1/chat/completions" || path == "/v1/completions" {
		client = g.textClient
	}
	response, e := client.Do(upstream)
	if e != nil {
		fail(w, 503, "lma_bound_phone_unreachable_retry_same_key")
		return
	}
	defer response.Body.Close()
	for _, h := range returned {
		if v := response.Header.Get(h); v != "" {
			w.Header().Set(h, v)
		}
	}
	if r.Method == "HEAD" || response.StatusCode == 304 || response.StatusCode == 204 {
		w.WriteHeader(response.StatusCode)
		return
	}
	mime := response.Header.Get("Content-Type")
	if strings.HasPrefix(mime, "text/event-stream") && strings.HasSuffix(path, "/events") {
		w.Header().Del("Content-Length")
		w.WriteHeader(response.StatusCode)
		scanner := bufio.NewScanner(response.Body)
		scanner.Buffer(make([]byte, 4096), 1<<20)
		for scanner.Scan() {
			line := scanner.Text()
			if strings.HasPrefix(line, "data: ") {
				var event Object
				if json.Unmarshal([]byte(strings.TrimPrefix(line, "data: ")), &event) != nil {
					continue
				}
				if remote := str(event["jobId"]); remote != "" {
					g.mu.Lock()
					id, err := g.bindLocked(p, c, "job", remote)
					if err == nil {
						event["jobId"] = id
						g.saveLocked()
					}
					g.mu.Unlock()
					if err != nil {
						return
					}
				}
				b, _ := json.Marshal(event)
				line = "data: " + string(b)
			}
			fmt.Fprintln(w, line)
			if f, ok := w.(http.Flusher); ok {
				f.Flush()
			}
		}
		return
	}
	if strings.HasPrefix(mime, "application/json") {
		b, e := io.ReadAll(io.LimitReader(response.Body, 32<<20+1))
		if e != nil || len(b) > 32<<20 {
			fail(w, 502, "lma_invalid_upstream_body")
			return
		}
		var doc Object
		if json.Unmarshal(b, &doc) != nil {
			fail(w, 502, "lma_invalid_upstream_json")
			return
		}
		g.mu.Lock()
		remoteJob := response.Header.Get("X-LMA-Job-ID")
		if remoteJob == "" && str(doc["object"]) == "lma.job" {
			remoteJob = str(doc["id"])
		}
		if namespace != "" {
			v := g.state.Intents[namespace]
			v.Remote = remoteJob
			g.state.Intents[namespace] = v
		}
		if terminal(str(doc["state"])) && remoteJob != "" {
			for key, v := range g.state.Intents {
				if v.Remote == remoteJob && v.Owner == p.Owner && v.AccountID == c.account.ID && v.Instance == c.registry.Instance && v.Finished == 0 {
					v.Finished = time.Now().UnixMilli()
					g.state.Intents[key] = v
				}
			}
		}
		e = g.rewriteLocked(p, c, doc)
		if job := response.Header.Get("X-LMA-Job-ID"); job != "" {
			var public string
			public, e = g.bindLocked(p, c, "job", job)
			if e == nil {
				w.Header().Set("X-LMA-Job-ID", public)
			}
		}
		if namespace != "" && terminal(str(doc["state"])) {
			v := g.state.Intents[namespace]
			v.Finished = time.Now().UnixMilli()
			g.state.Intents[namespace] = v
		}
		if e == nil {
			e = g.saveLocked()
		}
		g.mu.Unlock()
		if e != nil {
			fail(w, 503, "lma_durable_state_unavailable")
			return
		}
		encoded, _ := json.Marshal(doc)
		w.Header().Set("Content-Length", strconv.Itoa(len(encoded)))
		w.WriteHeader(response.StatusCode)
		if r.Method != "HEAD" {
			w.Write(encoded)
		}
		return
	}
	if id := response.Header.Get("X-LMA-Job-ID"); id != "" {
		g.mu.Lock()
		public, err := g.bindLocked(p, c, "job", id)
		if err == nil {
			err = g.saveLocked()
		}
		g.mu.Unlock()
		if err != nil {
			fail(w, 503, "lma_durable_state_unavailable")
			return
		}
		w.Header().Set("X-LMA-Job-ID", public)
	}
	w.WriteHeader(response.StatusCode)
	if r.Method != "HEAD" {
		io.CopyBuffer(w, io.LimitReader(response.Body, 8<<30), make([]byte, 64<<10))
	}
}
func terminal(s string) bool {
	return s == "succeeded" || s == "failed" || s == "cancelled" || s == "interrupted"
}

// Registry replacement is rejected as one transaction when aliases are ambiguous.
func publishedNames(a Account, models []Object) (map[string]string, error) {
	result := map[string]string{}
	for _, m := range models {
		mid := str(m["id"])
		result[mid] = mid
	}
	for alias, target := range a.Aliases {
		if !validID.MatchString(alias) || !validID.MatchString(target) {
			return nil, errors.New("Invalid local alias")
		}
		if result[target] == "" {
			continue
		}
		if old := result[alias]; old != "" && old != target {
			return nil, errors.New("Local alias collides with a model identity")
		}
		result[alias] = target
	}
	return result, nil
}
