package localgateway

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
	"sync"
	"time"
)

// One bounded event cache per phone serves all downstream subscribers. JSON
// polling leaves both of the phone's native SSE slots available to its owner.
type phoneEvents struct {
	mu      sync.Mutex
	updated time.Time
	cursor  int64
	floor   int64
	events  []Object
}

func (g *Gateway) pollEvents(ctx context.Context, c choice, after int64) ([]Object, int64, bool, error) {
	g.mu.Lock()
	cache := g.eventCache[c.account.ID]
	if cache == nil {
		cache = &phoneEvents{}
		g.eventCache[c.account.ID] = cache
	}
	g.mu.Unlock()
	cache.mu.Lock()
	defer cache.mu.Unlock()
	if time.Since(cache.updated) >= 500*time.Millisecond {
		bounded, cancel := context.WithTimeout(ctx, 5*time.Second)
		defer cancel()
		req, _ := http.NewRequestWithContext(bounded, "GET", c.account.BaseURL+"/v1/events?after="+strconv.FormatInt(cache.cursor, 10), nil)
		req.Header.Set("Authorization", "Bearer "+os.Getenv(c.account.KeyEnv))
		r, e := g.client.Do(req)
		if e != nil {
			return nil, 0, false, errors.New("Phone events unavailable")
		}
		defer r.Body.Close()
		b, e := io.ReadAll(io.LimitReader(r.Body, 2<<20+1))
		var doc Object
		if e != nil || r.StatusCode != 200 || len(b) > 2<<20 || json.Unmarshal(b, &doc) != nil {
			return nil, 0, false, errors.New("Invalid phone events")
		}
		for _, v := range array(doc["events"]) {
			event := object(v)
			seq, _ := event["sequence"].(float64)
			if int64(seq) > cache.cursor {
				cache.events = append(cache.events, event)
			}
		}
		cursor, _ := doc["cursor"].(float64)
		cache.cursor = int64(cursor)
		if len(cache.events) > 1024 {
			cache.events = cache.events[len(cache.events)-1024:]
		}
		if len(cache.events) > 0 {
			seq, _ := cache.events[0]["sequence"].(float64)
			cache.floor = int64(seq) - 1
		}
		cache.updated = time.Now()
	}
	result := []Object{}
	for _, event := range cache.events {
		seq, _ := event["sequence"].(float64)
		if int64(seq) > after {
			result = append(result, clone(event))
		}
	}
	return result, cache.cursor, after > 0 && after < cache.floor, nil
}

func (g *Gateway) eventStream(w http.ResponseWriter, r *http.Request, p Principal, c choice, remote string) {
	select {
	case g.eventClients <- struct{}{}:
		defer func() { <-g.eventClients }()
	default:
		fail(w, 503, "lma_event_subscriber_capacity")
		return
	}
	value := r.URL.Query().Get("after")
	header := r.Header.Get("Last-Event-ID")
	if value != "" && header != "" && value != header {
		fail(w, 400, "lma_event_cursor_conflict")
		return
	}
	if value == "" {
		value = header
	}
	if value == "" {
		value = "0"
	}
	after, e := strconv.ParseInt(value, 10, 64)
	if e != nil || after < 0 {
		fail(w, 400, "lma_event_cursor_invalid")
		return
	}
	for name := range r.URL.Query() {
		if name != "after" {
			fail(w, 400, "lma_unsupported_query")
			return
		}
	}
	ctx, cancel := context.WithTimeout(r.Context(), 120*time.Second)
	defer cancel()
	started := false
	for {
		events, cursor, reset, e := g.pollEvents(ctx, c, after)
		if e != nil {
			if !started {
				fail(w, 503, "lma_phone_events_unavailable")
			}
			return
		}
		if !started {
			w.Header().Set("Content-Type", "text/event-stream")
			w.Header().Set("Cache-Control", "no-store")
			w.Header().Set("X-Accel-Buffering", "no")
			w.WriteHeader(200)
			started = true
		}
		if reset {
			fmt.Fprintf(w, "event: reset\ndata: {\"truncated\":true,\"cursor\":%d}\n\n", cursor)
		}
		finished := false
		for _, event := range events {
			if str(event["jobId"]) != remote {
				continue
			}
			g.mu.Lock()
			public, err := g.bindLocked(p, c, "job", remote)
			g.mu.Unlock()
			if err != nil {
				return
			}
			event["jobId"] = public
			data, _ := json.Marshal(event)
			fmt.Fprintf(w, "id: %.0f\nevent: job\ndata: %s\n\n", event["sequence"], data)
			finished = finished || terminal(str(event["state"]))
		}
		after = cursor
		fmt.Fprint(w, ": heartbeat\n\n")
		if f, ok := w.(http.Flusher); ok {
			f.Flush()
		}
		if finished {
			return
		}
		select {
		case <-ctx.Done():
			return
		case <-g.closed:
			return
		case <-time.After(500 * time.Millisecond):
		}
	}
}
