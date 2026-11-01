package com.lma.app.core;

import org.json.JSONArray;
import org.json.JSONObject;
import java.util.*;

/** Explicit OpenAI subset mapping; no guessed modes, remote inputs or silent field loss. */
public final class OpenAiRequests {
    private OpenAiRequests() {}
    public static void fields(JSONObject source, String... allowed) throws Exception {
        Set<String> names = new HashSet<>(Arrays.asList(allowed));
        for (Iterator<String> it = source.keys(); it.hasNext();) { String name = it.next(); if (!names.contains(name)) throw invalid(name, "Unsupported request field: " + name); }
    }
    public static LocalHttp.Failure invalid(String field, String message) { return new LocalHttp.Failure(400, "lma_unsupported_" + field.replaceAll("[^A-Za-z0-9_]", "_"), message); }
    public static JSONObject model(LocalApi.Runtime runtime, String id, String operation) throws Exception {
        JSONObject model = runtime.model(id); JSONArray operations = model.getJSONObject("x_lma").getJSONArray("operations");
        for (int i = 0; i < operations.length(); i++) if (operations.getString(i).equals(operation)) return model;
        throw invalid("model", "The selected model does not implement " + operation);
    }
    private static JSONObject options(JSONObject raw) throws Exception {
        JSONObject options = raw.optJSONObject("lma");
        if (raw.has("lma") && options == null) throw invalid("lma", "lma must be an object");
        if (options == null) options = new JSONObject();
        fields(options, "allow_unmeasured", "parameters", "adapters", "artifacts", "transcripts");
        if (options.has("allow_unmeasured") && !(options.get("allow_unmeasured") instanceof Boolean)) throw invalid("allow_unmeasured", "Use an explicit boolean");
        if (options.has("parameters") && !(options.get("parameters") instanceof JSONObject)) throw invalid("parameters", "parameters must be an object");
        return options;
    }
    public static JSONObject image(JSONObject raw) throws Exception {
        fields(raw, "model", "prompt", "n", "size", "quality", "background", "response_format", "output_format", "stream", "lma");
        if (raw.has("n") && (!(raw.get("n") instanceof Number) || raw.getDouble("n") != 1)) throw invalid("n", "This facade supports n=1");
        if (raw.has("stream") && (!(raw.get("stream") instanceof Boolean) || raw.getBoolean("stream"))) throw invalid("stream", "Image output is a complete PNG; use job events for progress");
        if (!raw.optString("response_format", "b64_json").equals("b64_json")) throw invalid("response_format", "Use b64_json");
        if (!raw.optString("output_format", "png").equals("png")) throw invalid("output_format", "Only PNG is supported");
        if (raw.has("quality")) throw invalid("quality", "Use the selected model's explicit lma.parameters instead of an unmapped quality preset");
        if (raw.has("background") && !Arrays.asList("opaque", "auto").contains(raw.getString("background"))) throw invalid("background", "Transparent background is not a declared image capability");
        JSONObject options = options(raw), parameters = options.has("parameters") ? DataFiles.copy(options.getJSONObject("parameters")) : new JSONObject();
        String size = raw.optString("size", "auto");
        if (!size.equals("auto")) {
            if (!size.matches("[1-9][0-9]{0,4}x[1-9][0-9]{0,4}")) throw invalid("size", "Use auto or WIDTHxHEIGHT");
            String[] shape = size.split("x"); parameters.put("width", Integer.parseInt(shape[0])).put("height", Integer.parseInt(shape[1]));
        }
        JSONObject input = new JSONObject().put("prompt", raw.getString("prompt")); copyInputs(options, input);
        JSONObject result = new JSONObject().put("model", raw.getString("model")).put("type", "image.generate").put("input", input).put("parameters", parameters).put("allowUnmeasured", options.optBoolean("allow_unmeasured", false));
        if (options.has("adapters")) result.put("adapters", options.getJSONArray("adapters")); return result;
    }
    public static JSONObject speech(JSONObject raw, LocalApi.Runtime runtime) throws Exception {
        fields(raw, "model", "input", "voice", "response_format", "speed", "stream_format", "lma");
        if (!raw.optString("response_format", "mp3").equals("wav")) throw invalid("response_format", "This phone facade supports WAV. Missing response_format requests MP3, which is unsupported");
        if (!raw.optString("stream_format", "audio").equals("audio")) throw invalid("stream_format", "Use whole-file audio; stage events and PCM previews are separate capabilities");
        JSONObject model = model(runtime, raw.getString("model"), "speech.synthesize"), properties = model.getJSONObject("x_lma").getJSONObject("parameter_schema").getJSONObject("properties");
        JSONObject options = options(raw), parameters = options.has("parameters") ? DataFiles.copy(options.getJSONObject("parameters")) : new JSONObject();
        String voice = raw.getString("voice");
        if (!voice.equals("default")) {
            if (properties.has("speaker") && voice.matches("[0-9]{1,4}")) {
                int speaker = Integer.parseInt(voice); JSONObject field = properties.getJSONObject("speaker");
                if (speaker < field.optInt("minimum", 0) || speaker > field.optInt("maximum", Integer.MAX_VALUE)) throw invalid("voice", "Unknown speaker");
                parameters.put("speaker", speaker);
            } else if (properties.has("voice") && contains(properties.getJSONObject("voice").optJSONArray("enum"), voice)) parameters.put("voice", voice);
            else throw invalid("voice", "Use default or an explicitly advertised speaker/voice");
        }
        if (raw.has("speed")) {
            if (!properties.has("speed") || !(raw.get("speed") instanceof Number) || !Double.isFinite(raw.getDouble("speed")) || raw.getDouble("speed") <= 0) throw invalid("speed", "This model requires a supported positive speed value");
            parameters.put("speed", raw.getDouble("speed"));
        }
        JSONObject input = new JSONObject().put("prompt", raw.getString("input")); copyInputs(options, input);
        return new JSONObject().put("model", raw.getString("model")).put("type", "speech.synthesize").put("input", input).put("parameters", parameters).put("allowUnmeasured", options.optBoolean("allow_unmeasured", false));
    }
    private static void copyInputs(JSONObject options, JSONObject input) throws Exception {
        if (options.has("artifacts")) input.put("artifacts", options.getJSONArray("artifacts"));
        if (options.has("transcripts")) input.put("transcripts", options.getJSONObject("transcripts"));
    }
    private static boolean contains(JSONArray values, String value) throws Exception { if (values != null) for (int i = 0; i < values.length(); i++) if (values.getString(i).equals(value)) return true; return false; }
    public static JSONObject nativeTask(JSONObject raw, LocalApi.Runtime runtime) throws Exception {
        fields(raw, "model", "type", "input", "parameters", "allowUnmeasured", "adapters");
        JSONObject model = model(runtime, raw.getString("model"), raw.getString("type"));
        JSONObject result = DataFiles.copy(raw); result.remove("model"); result.put("bundleId", model.getString("bundle_id"));
        if (result.has("adapters")) {
            JSONArray adapters = result.getJSONArray("adapters"), nativeAdapters = new JSONArray();
            for (int i = 0; i < adapters.length(); i++) {
                JSONObject adapter = adapters.getJSONObject(i); fields(adapter, "model", "scale");
                JSONObject selected = new JSONObject().put("bundleId", runtime.adapter(adapter.getString("model")));
                if (adapter.has("scale")) selected.put("scale", adapter.get("scale")); nativeAdapters.put(selected);
            }
            result.put("adapters", nativeAdapters);
        }
        return TaskInput.validate(result);
    }
}
