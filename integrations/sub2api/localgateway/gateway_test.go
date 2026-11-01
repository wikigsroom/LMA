package localgateway

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
)

type phoneFixture struct {
	mu          sync.Mutex
	instance    string
	revision    string
	generation  int
	conditional int
	bodies      []Object
	headers     []http.Header
	seen        map[string]string
	received    int
	rangeSeen   bool
}

func (f *phoneFixture) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	f.mu.Lock()
	defer f.mu.Unlock()
	w.Header().Set("Content-Type", "application/json")
	if r.Header.Get("Authorization") != "Bearer fixture-parent-key" {
		w.WriteHeader(401)
		return
	}
	if r.URL.Path == "/v1/models" {
		if r.Header.Get("If-None-Match") == f.revision {
			f.conditional++
			w.WriteHeader(304)
			return
		}
		w.Header().Set("ETag", f.revision)
		models := []Object{}
		for _, pair := range [][2]string{{"image_fixture", "image.generate"}, {"speech_fixture", "speech.synthesize"}, {"video_fixture", "video.generate"}, {"mesh_fixture", "mesh.generate"}, {"text_fixture", "text.generate"}, {"music_fixture", "audio.generate"}} {
			models = append(models, Object{"id": pair[0], "object": "model", "owned_by": "local", "x_lma": Object{"publication": Object{"eligible": true}, "operations": []string{pair[1]}, "saved_parameters": Object{"steps": 4}, "ready": Object{"loaded": false, "available": true}}})
		}
		json.NewEncoder(w).Encode(Object{"object": "list", "data": models, "x_lma": Object{"schema": "lma.catalogue/1", "instance_id": f.instance}})
		return
	}
	if r.Method == "POST" && (r.URL.Path == "/v1/lma/jobs" || r.URL.Path == "/v1/images/generations" || r.URL.Path == "/v1/audio/speech") {
		var body Object
		json.NewDecoder(r.Body).Decode(&body)
		f.bodies = append(f.bodies, body)
		f.headers = append(f.headers, r.Header.Clone())
		key := r.Header.Get("Idempotency-Key")
		id := f.seen[key]
		if id == "" {
			f.generation++
			id = "job_fixture_" + string(rune('a'+f.generation))
			f.seen[key] = id
		}
		w.Header().Set("X-LMA-Job-ID", id)
		if r.URL.Path == "/v1/images/generations" {
			json.NewEncoder(w).Encode(Object{"created": 1, "data": []Object{{"b64_json": "aW1hZ2U="}}, "x_lma": Object{"job_id": id}})
			return
		}
		if r.URL.Path == "/v1/audio/speech" {
			w.Header().Set("Content-Type", "audio/wav")
			w.Write([]byte("RIFF-fixture-WAVE"))
			return
		}
		w.WriteHeader(202)
		json.NewEncoder(w).Encode(Object{"id": id, "object": "lma.job", "model": body["model"], "state": "queued", "outputs": []any{}})
		return
	}
	if r.URL.Path == "/v1/lma/uploads" && r.Method == "POST" {
		w.WriteHeader(202)
		json.NewEncoder(w).Encode(Object{"id": "upload_fixture", "object": "lma.upload", "received": 0})
		return
	}
	if strings.HasSuffix(r.URL.Path, "/complete") {
		json.NewEncoder(w).Encode(Object{"id": "artifact_input", "object": "lma.artifact", "mime": "image/png", "bytes": 8, "content_path": "/v1/lma/artifacts/artifact_input/content"})
		return
	}
	if r.Method == "PUT" {
		f.received++
		if r.Header.Get("Upload-Offset") != "0" {
			w.WriteHeader(409)
			return
		}
		json.NewEncoder(w).Encode(Object{"id": "upload_fixture", "object": "lma.upload", "received": 8})
		return
	}
	if strings.Contains(r.URL.Path, "/artifacts/") && strings.HasSuffix(r.URL.Path, "/content") {
		w.Header().Set("Content-Type", "image/png")
		w.Header().Set("ETag", "\"artifact-etag\"")
		if r.Header.Get("If-None-Match") == "\"artifact-etag\"" {
			w.WriteHeader(304)
			return
		}
		if r.Header.Get("Range") == "bytes=0-3" {
			f.rangeSeen = r.Header.Get("If-Range") == "\"artifact-etag\""
			w.Header().Set("Content-Range", "bytes 0-3/8")
			w.WriteHeader(206)
			w.Write([]byte("PNG!"))
			return
		}
		w.Write([]byte("PNG!data"))
		return
	}
	if strings.HasSuffix(r.URL.Path, "/events") {
		if r.Header.Get("Accept") == "text/event-stream" {
			w.Header().Set("Content-Type", "text/event-stream")
			w.Write([]byte("id: 7\nevent: job\ndata: {\"jobId\":\"job_fixture_b\",\"state\":\"succeeded\"}\n\n"))
			return
		}
		json.NewEncoder(w).Encode(Object{"events": []Object{{"jobId": "job_fixture_b", "state": "succeeded", "sequence": 7}}, "cursor": 7})
		return
	}
	if strings.Contains(r.URL.Path, "/jobs/") {
		parts := strings.Split(r.URL.Path, "/")
		json.NewEncoder(w).Encode(Object{"id": parts[4], "object": "lma.job", "model": "image_fixture", "state": "succeeded", "outputs": []Object{{"id": "artifact_fixture", "object": "lma.artifact", "mime": "image/png", "bytes": 8, "content_path": "/v1/lma/artifacts/artifact_fixture/content"}}})
		return
	}
	w.WriteHeader(404)
}
func setup(t *testing.T) (*Gateway, *phoneFixture, *httptest.Server, Config) {
	t.Helper()
	t.Setenv("LMA_TEST_PARENT_KEY", "fixture-parent-key")
	f := &phoneFixture{instance: "lma_fixture_phone", revision: "\"r1\"", seen: map[string]string{}}
	server := httptest.NewServer(f)
	t.Cleanup(server.Close)
	cfg := Config{StateFile: filepath.Join(t.TempDir(), "gateway.json"), Accounts: []Account{{ID: 1, GroupID: 2, BaseURL: server.URL, KeyEnv: "LMA_TEST_PARENT_KEY", Aliases: map[string]string{"my_image": "image_fixture"}}}}
	g, e := New(cfg)
	if e != nil {
		t.Fatal(e)
	}
	t.Cleanup(g.Close)
	if e = g.Sync(context.Background(), 1); e != nil {
		t.Fatal(e)
	}
	return g, f, server, cfg
}
func call(g *Gateway, p Principal, method, path, body string, headers ...string) *httptest.ResponseRecorder {
	r := httptest.NewRequest(method, path, strings.NewReader(body))
	r.Header.Set("Content-Type", "application/json")
	for i := 0; i < len(headers); i += 2 {
		r.Header.Set(headers[i], headers[i+1])
	}
	w := httptest.NewRecorder()
	g.ServeHTTP(w, r, p)
	return w
}
func decoded(t *testing.T, w *httptest.ResponseRecorder) Object {
	t.Helper()
	var o Object
	if json.Unmarshal(w.Body.Bytes(), &o) != nil {
		t.Fatalf("Invalid JSON: status=%d", w.Code)
	}
	return o
}
func TestCataloguePermissionsAndStaleness(t *testing.T) {
	g, f, _, _ := setup(t)
	p := Principal{Owner: "alice", GroupID: 2}
	w := call(g, p, "GET", "/v1/models", "")
	if w.Code != 200 || len(array(decoded(t, w)["data"])) != 7 {
		t.Fatal("all six modalities and explicit alias must be auto-published")
	}
	if call(g, p, "GET", "/v1/models", "", "If-None-Match", w.Header().Get("ETag")).Code != 304 {
		t.Fatal("conditional catalogue")
	}
	if call(g, p, "HEAD", "/v1/models", "").Body.Len() != 0 {
		t.Fatal("HEAD has no body")
	}
	limited := Principal{Owner: "restricted", GroupID: 2, Allows: func(m string) bool { return m == "image_fixture" }}
	if len(array(decoded(t, call(g, limited, "GET", "/v1/models", ""))["data"])) != 1 {
		t.Fatal("group allowlist must filter discovery")
	}
	if call(g, Principal{Owner: "other", GroupID: 3}, "GET", "/v1/models", "").Code != 403 {
		t.Fatal("group cannot cross accounts")
	}
	if e := g.Sync(context.Background(), 1); e != nil || f.conditional != 1 {
		t.Fatal("304 sync")
	}
	g.mu.Lock()
	r := g.state.Registries[1]
	r.LastSuccess = time.Now().Add(-100 * time.Second).UnixMilli()
	g.state.Registries[1] = r
	g.mu.Unlock()
	w = call(g, p, "GET", "/v1/models", "")
	if w.Code != 200 || object(object(object(array(decoded(t, w)["data"])[0])["x_lma"])["ready"])["available"] != false {
		t.Fatal("offline keeps last metadata unavailable")
	}
	if call(g, p, "POST", "/v1/lma/jobs", `{"model":"image_fixture","type":"image.generate","input":{"prompt":"fixture"}}`, "Idempotency-Key", "new").Code != 503 {
		t.Fatal("stale phone cannot admit new jobs")
	}
}
func TestDurableRetriesOwnershipAndArtifacts(t *testing.T) {
	g, f, _, cfg := setup(t)
	p := Principal{Owner: "alice", GroupID: 2}
	body := `{"model":"my_image","type":"image.generate","input":{"prompt":"owned cube"}}`
	w := call(g, p, "POST", "/v1/lma/jobs", body, "Idempotency-Key", "one")
	if w.Code != 202 {
		t.Fatalf("submit status %d", w.Code)
	}
	id := str(decoded(t, w)["id"])
	if !strings.HasPrefix(id, "lma_job_") || f.generation != 1 || str(f.bodies[0]["model"]) != "image_fixture" {
		t.Fatal("capability routing uses real model and public owner binding")
	}
	if object(f.bodies[0]["parameters"])["steps"] != float64(4) {
		t.Fatal("freeze model settings before first write")
	}
	if f.headers[0].Get("Authorization") != "Bearer fixture-parent-key" || !strings.HasPrefix(f.headers[0].Get("Idempotency-Key"), "gw_") {
		t.Fatal("separate parent credential and caller key namespace")
	}
	restarted, e := New(cfg)
	if e != nil {
		t.Fatal(e)
	}
	defer restarted.Close()
	if call(restarted, p, "POST", "/v1/lma/jobs", body, "Idempotency-Key", "one").Code != 202 || f.generation != 1 {
		t.Fatal("durable replay is same phone and same frozen body")
	}
	if call(g, p, "POST", "/v1/lma/jobs", strings.ReplaceAll(body, "owned cube", "different"), "Idempotency-Key", "one").Code != 409 {
		t.Fatal("body conflict")
	}
	if call(g, Principal{Owner: "bob", GroupID: 2}, "GET", "/v1/lma/jobs/"+id, "").Code != 404 {
		t.Fatal("cross owner job leak")
	}
	detail := decoded(t, call(g, p, "GET", "/v1/lma/jobs/"+id, ""))
	artifact := object(array(detail["outputs"])[0])
	path := str(artifact["content_path"])
	if !strings.Contains(path, "lma_artifact_") {
		t.Fatal("artifact binding is rewritten")
	}
	if call(g, Principal{Owner: "bob", GroupID: 2}, "GET", path, "").Code != 404 {
		t.Fatal("cross owner artifact leak")
	}
	rangeReply := call(g, p, "GET", path, "", "Range", "bytes=0-3", "If-Range", "\"artifact-etag\"")
	if rangeReply.Code != 206 || rangeReply.Body.String() != "PNG!" || !f.rangeSeen {
		t.Fatal("Range and If-Range forwarding")
	}
	if call(g, p, "GET", path, "", "If-None-Match", "\"artifact-etag\"").Code != 304 {
		t.Fatal("conditional artifact")
	}
	if call(g, p, "HEAD", path, "").Body.Len() != 0 {
		t.Fatal("artifact HEAD")
	}
	events := decoded(t, call(g, p, "GET", "/v1/lma/jobs/"+id+"/events", ""))
	if str(object(array(events["events"])[0])["jobId"]) != id {
		t.Fatal("JSON event owner namespace")
	}
	sse := call(g, p, "GET", "/v1/lma/jobs/"+id+"/events", "", "Accept", "text/event-stream", "Last-Event-ID", "6")
	if sse.Code != 200 || !strings.Contains(sse.Body.String(), id) || strings.Contains(sse.Body.String(), "job_fixture_b") {
		t.Fatal("SSE event rewriting")
	}
	if call(g, Principal{Owner: "bob", GroupID: 2}, "POST", "/v1/lma/jobs", body, "Idempotency-Key", "one").Code != 202 || f.generation != 2 {
		t.Fatal("different caller key namespaces")
	}
}
func TestUploadsAndBoundInputs(t *testing.T) {
	g, f, _, _ := setup(t)
	p := Principal{Owner: "alice", GroupID: 2}
	u := decoded(t, call(g, p, "POST", "/v1/lma/uploads", `{"model":"mesh_fixture","name":"owned.png","bytes":8}`))
	id := str(u["id"])
	if !strings.HasPrefix(id, "lma_upload_") {
		t.Fatal("upload binding")
	}
	if call(g, p, "PUT", "/v1/lma/uploads/"+id, "12345678", "Content-Type", "application/octet-stream", "Upload-Offset", "0").Code != 200 || f.received != 1 {
		t.Fatal("chunk offset")
	}
	if call(g, Principal{Owner: "bob", GroupID: 2}, "DELETE", "/v1/lma/uploads/"+id, "").Code != 404 {
		t.Fatal("upload owner")
	}
	a := decoded(t, call(g, p, "POST", "/v1/lma/uploads/"+id+"/complete", `{}`))
	body := `{"model":"mesh_fixture","type":"mesh.generate","input":{"artifacts":[{"role":"reference_image","artifactId":"` + str(a["id"]) + `"}]}}`
	if call(g, p, "POST", "/v1/lma/jobs", body, "Idempotency-Key", "mesh").Code != 202 {
		t.Fatal("owned input reference")
	}
	if str(object(array(object(f.bodies[len(f.bodies)-1]["input"])["artifacts"])[0])["artifactId"]) != "artifact_input" {
		t.Fatal("input translated only for same phone")
	}
	if call(g, Principal{Owner: "bob", GroupID: 2}, "POST", "/v1/lma/jobs", body, "Idempotency-Key", "mesh").Code != 404 {
		t.Fatal("cross caller input cannot be attached")
	}
}
func TestOpenAIImageAndSpeech(t *testing.T) {
	g, _, _, _ := setup(t)
	p := Principal{Owner: "alice", GroupID: 2}
	image := call(g, p, "POST", "/v1/images/generations", `{"model":"image_fixture","prompt":"cube"}`, "Idempotency-Key", "image")
	if image.Code != 200 || !strings.HasPrefix(image.Header().Get("X-LMA-Job-ID"), "lma_job_") {
		t.Fatal("arbitrary real model image route bypasses GPT family gate")
	}
	speech := call(g, p, "POST", "/v1/audio/speech", `{"model":"speech_fixture","input":"hello","voice":"default","response_format":"wav"}`, "Idempotency-Key", "speech")
	if speech.Code != 200 || speech.Header().Get("Content-Type") != "audio/wav" || !strings.HasPrefix(speech.Body.String(), "RIFF") {
		t.Fatal("generic phone speech byte route")
	}
}
func TestUnavailableFirstFetchAndInstanceChange(t *testing.T) {
	g, f, _, cfg := setup(t)
	p := Principal{Owner: "alice", GroupID: 2}
	f.mu.Lock()
	f.instance = "changed-phone"
	f.revision = "\"changed\""
	f.mu.Unlock()
	if g.Sync(context.Background(), 1) == nil {
		t.Fatal("instance changes require explicit reconfiguration")
	}
	cfg.StateFile = filepath.Join(t.TempDir(), "new.json")
	empty, e := New(cfg)
	if e != nil {
		t.Fatal(e)
	}
	defer empty.Close()
	if call(empty, p, "GET", "/v1/models", "").Code != 503 {
		t.Fatal("never fall back to cloud catalogue before first fetch")
	}
}
func TestLimitsAndRoutes(t *testing.T) {
	g, _, _, _ := setup(t)
	p := Principal{Owner: "alice", GroupID: 2}
	for _, tc := range []struct {
		method, path, body string
		headers            []string
		status             int
	}{{"POST", "/v1/lma/jobs", `{"model":"image_fixture","type":"image.generate"}`, nil, 400}, {"POST", "/v1/lma/jobs", strings.Repeat("x", 256<<10+1), nil, 413}, {"GET", "/v1/models", "", []string{"Origin", "https://example.invalid"}, 403}, {"POST", "/v1/responses", `{}`, nil, 404}, {"GET", "/v1/lma/jobs/unknown", "", nil, 404}, {"GET", "/v1/models/missing", "", nil, 404}, {"POST", "/v1/lma/jobs", `{broken}`, nil, 400}} {
		if w := call(g, p, tc.method, tc.path, tc.body, tc.headers...); w.Code != tc.status {
			t.Fatalf("%s %s: got %d want %d", tc.method, tc.path, w.Code, tc.status)
		}
	}
}
func TestPrivateOriginValidation(t *testing.T) {
	g, _, _, cfg := setup(t)
	_ = g
	cfg.Accounts[0].BaseURL = "http://user:password@127.0.0.1"
	if _, e := New(cfg); e == nil {
		t.Fatal("credentials in URL forbidden")
	}
	cfg.Accounts[0].BaseURL = "https://example.org"
	cfg.StateFile = filepath.Join(t.TempDir(), "private.json")
	remote, e := New(cfg)
	if e != nil {
		t.Fatal(e)
	}
	defer remote.Close()
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	if remote.Sync(ctx, 1) == nil {
		t.Fatal("public cloud origin must not be contacted")
	}
}
func TestNoLeakedParentCredential(t *testing.T) {
	g, _, _, cfg := setup(t)
	p := Principal{Owner: "alice", GroupID: 2}
	w := call(g, p, "GET", "/v1/models", "")
	if strings.Contains(w.Body.String(), "fixture-parent-key") || strings.Contains(w.Body.String(), cfg.StateFile) {
		t.Fatal("credential or private path leak")
	}
	_ = io.Discard
}

func TestAtomicAliasConflicts(t *testing.T) {
	g, _, _, cfg := setup(t)
	g.mu.Lock()
	before := g.state.Registries[1]
	account := g.accounts[1]
	account.Aliases = map[string]string{"image_fixture": "speech_fixture"}
	g.accounts[1] = account
	g.mu.Unlock()
	// Force a full fetch rather than 304.
	g.mu.Lock()
	old := g.state.Registries[1]
	old.ETag = ""
	g.state.Registries[1] = old
	g.mu.Unlock()
	if g.Sync(context.Background(), 1) == nil {
		t.Fatal("An alias must not shadow another native model")
	}
	if g.state.Registries[1].LastSuccess != before.LastSuccess {
		t.Fatal("Conflict replaced a last-good registry")
	}
	_ = cfg
}
func TestSharedEventsBoundedAndPrivate(t *testing.T) {
	g, _, _, _ := setup(t)
	p := Principal{Owner: "alice", GroupID: 2}
	job := decoded(t, call(g, p, "POST", "/v1/lma/jobs", `{"model":"video_fixture","type":"video.generate"}`, "Idempotency-Key", "events-shared"))
	id := str(job["id"])
	for i := 0; i < 3; i++ {
		w := call(g, p, "GET", "/v1/lma/jobs/"+id+"/events", "", "Accept", "text/event-stream", "Last-Event-ID", "6")
		if w.Code != 200 || !strings.Contains(w.Body.String(), id) || strings.Contains(w.Body.String(), "job_fixture_b") {
			t.Fatal("Private event IDs must be mapped")
		}
	}
	if len(g.eventCache) != 1 || len(g.eventClients) != 0 {
		t.Fatal("Shared cache or subscriber cleanup")
	}
	if call(g, Principal{Owner: "bob", GroupID: 2}, "GET", "/v1/lma/jobs/"+id+"/events", "", "Accept", "text/event-stream").Code != 404 {
		t.Fatal("Event ownership")
	}
}

// A shortened ordinary header budget reproduces a long text prefill without
// making the suite wait130 seconds. The control request must still time out.
func TestTextPrefillOutlivesOrdinaryHeaderBudget(t *testing.T) {
	t.Setenv("LMA_TEST_PARENT_KEY", "fixture-parent-key")
	f := &phoneFixture{instance: "lma_fixture_phone", revision: "\"r1\"", seen: map[string]string{}}
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/v1/chat/completions" || r.URL.Path == "/slow-header" {
			time.Sleep(80 * time.Millisecond)
			w.Header().Set("Content-Type", "application/json")
			io.WriteString(w, `{"model":"text_fixture","choices":[{"message":{"role":"assistant","content":"ready"}}]}`)
			return
		}
		f.ServeHTTP(w, r)
	}))
	defer server.Close()
	cfg := Config{StateFile: filepath.Join(t.TempDir(), "gateway.json"), Accounts: []Account{{ID: 1, GroupID: 2, BaseURL: server.URL, KeyEnv: "LMA_TEST_PARENT_KEY"}}}
	g, e := New(cfg)
	if e != nil {
		t.Fatal(e)
	}
	defer g.Close()
	if e = g.Sync(context.Background(), 1); e != nil {
		t.Fatal(e)
	}
	g.client.Transport.(*http.Transport).ResponseHeaderTimeout = 20 * time.Millisecond
	w := call(g, Principal{Owner: "alice", GroupID: 2}, "POST", "/v1/chat/completions", `{"model":"text_fixture","messages":[{"role":"user","content":"hello"}]}`)
	if w.Code != 200 || !strings.Contains(w.Body.String(), "ready") {
		t.Fatalf("long text prefill was stopped: status%d", w.Code)
	}
	response, e := g.client.Get(server.URL + "/slow-header")
	if response != nil {
		response.Body.Close()
	}
	if e == nil {
		t.Fatal("ordinary network header guard must remain independent")
	}
}
