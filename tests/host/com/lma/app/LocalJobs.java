package com.lma.app;

import org.json.JSONObject;

/** Host port only; these backend checks exercise the actual gateway/text proxy, not Android jobs. */
public final class LocalJobs {
    public boolean busy() { return false; }
    public String activeId() { return ""; }
    public JSONObject submit(JSONObject request, String key) throws Exception { throw new java.io.IOException("Android job execution is unavailable in this host port"); }
    public void cancel(String id) throws Exception { throw new java.io.IOException("Android job execution is unavailable in this host port"); }
}
