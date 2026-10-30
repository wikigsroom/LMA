package com.lma.app.core;

import org.json.*;
import java.io.*;
import java.util.*;

/** Bounded local-file presentation metadata. No voices, prompt codes or model weights are embedded. */
public final class SpeechVoices {
    private static final class Voices {
        final int count; final List<String> names;
        Voices(int count, List<String> names) throws IOException {
            if (count < 1 || count > 128 || !names.isEmpty() && names.size() != count) throw new IOException("Invalid local voice count");
            this.count = count; this.names = Collections.unmodifiableList(new ArrayList<>(names));
        }
    }
    private final Map<String, Voices> cache = new LinkedHashMap<String, Voices>(16, 0.75f, true) {
        @Override protected boolean removeEldestEntry(Map.Entry<String, Voices> entry) { return size() > 32; }
    };
    public synchronized ParameterSchema onnx(ParameterSchema schema, File file) throws Exception {
        String key = "onnx:" + identity(file); Voices value = cache.get(key);
        if (value == null) {
            Map<String, String> meta = OnnxMetadata.read(file);
            if (!meta.containsKey("n_speakers")) return unavailable(schema);
            int count;
            try { count = Integer.parseInt(meta.get("n_speakers")); } catch (NumberFormatException invalid) { throw new IOException("Invalid local voice count"); }
            List<String> names = new ArrayList<>();
            if (meta.containsKey("speaker_names")) names.addAll(Arrays.asList(meta.get("speaker_names").split(",", -1)));
            if (meta.containsKey("id2speaker")) {
                if (count < 1 || count > 128) throw new IOException("Invalid local voice count");
                String[] mapped = new String[count];
                for (String pair : meta.get("id2speaker").split(",", -1)) {
                    int split = pair.indexOf("->"), index;
                    if (split < 1) throw new IOException("Invalid local voice mapping");
                    try { index = Integer.parseInt(pair.substring(0, split)); } catch (NumberFormatException invalid) { throw new IOException("Invalid local voice mapping"); }
                    if (index < 0 || index >= count || mapped[index] != null) throw new IOException("Duplicate or excessive local voice mapping");
                    mapped[index] = pair.substring(split + 2);
                }
                for (String name : mapped) if (name == null) throw new IOException("Incomplete local voice mapping");
                if (!names.isEmpty() && !names.equals(Arrays.asList(mapped))) throw new IOException("Conflicting local voice names");
                names = Arrays.asList(mapped);
            }
            value = new Voices(count, names); cache.put(key, value);
        }
        return apply(schema, value);
    }
    public synchronized ParameterSchema nano(ParameterSchema schema, File file) throws Exception {
        String key = "nano:" + identity(file); Voices value = cache.get(key);
        if (value == null) {
            JSONArray rows = MossNanoSpec.readMetadata(file).getJSONArray("builtin_voices");
            List<String> names = new ArrayList<>();
            if (rows.length() < 1 || rows.length() > 128) throw new IOException("Invalid local voice count");
            for (int i = 0; i < rows.length(); i++) names.add(rows.getJSONObject(i).optString("display_name", ""));
            value = new Voices(rows.length(), names); cache.put(key, value);
        }
        return apply(schema, value);
    }
    private static String identity(File file) throws IOException {
        if (!file.isFile() || file.length() < 1) throw new IOException("Local voice metadata is unavailable");
        return file.getCanonicalPath() + ":" + file.length() + ":" + file.lastModified();
    }
    private static boolean label(String text) {
        if (text == null || text.isEmpty() || text.length() > 80 || !text.equals(text.trim())) return false;
        for (int i = 0; i < text.length(); i++) if (Character.isISOControl(text.charAt(i))) return false;
        return true;
    }
    private static ParameterSchema apply(ParameterSchema schema, Voices voices) throws Exception {
        JSONObject json = schema.json(), fields = json.optJSONObject("fields");
        if (fields == null || !fields.has("speaker")) return schema;
        JSONObject field = fields.getJSONObject("speaker");
        if (!field.optString("type").equals("integer")) return schema;
        int maximum = Math.min(field.optInt("maximum", voices.count - 1), voices.count - 1);
        if (field.optInt("minimum", 0) > maximum) throw new IOException("Declared voice range exceeds this model's voice count");
        field.put("maximum", maximum).put("limitSource", "model_metadata").put("actualVoiceCount", voices.count);
        JSONArray choices = new JSONArray();
        for (int i = Math.max(0, field.optInt("minimum", 0)); i <= maximum; i++) {
            if (!voices.names.isEmpty() && label(voices.names.get(i))) choices.put(new JSONObject().put("value", i).put("label", voices.names.get(i)));
        }
        field.remove("choices"); if (choices.length() > 0) field.put("choices", choices);
        field.put("help", choices.length() > 0 ? "音色名称来自已下载的模型文件，也可直接输入编号；名称不扩展当前配方的语言能力。" : "已读取模型音色数量；文件未提供名称，请按编号选择。");
        return new ParameterSchema(json);
    }
    public static ParameterSchema unavailable(ParameterSchema schema) throws JSONException {
        JSONObject json = schema.json(), fields = json.optJSONObject("fields");
        if (fields != null && fields.has("speaker")) {
            JSONObject field = fields.getJSONObject("speaker"); field.remove("choices");
            field.put("help", "音色元数据暂不可读，按配方范围选择编号；生成时仍会核对实际音色。");
        }
        return new ParameterSchema(json);
    }
}
