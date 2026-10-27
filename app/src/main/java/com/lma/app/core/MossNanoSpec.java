package com.lma.app.core;

import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Exact ONNX Nano pipeline contract, with independent application guards and user-owned data. */
public final class MossNanoSpec {
    private MossNanoSpec() {}
    private static final Set<String> JSON = new HashSet<>(Arrays.asList("manifest", "tts_meta", "codec_meta"));
    private static final Set<String> GRAPHS = new HashSet<>(Arrays.asList("tts_prefill", "tts_decode", "tts_local", "codec_decode"));
    public static void validate(ModelBundle bundle, String type) throws Exception {
        if (!bundle.engine.equals("moss_nano_ort") || !bundle.pipeline.equals("moss_nano") || !bundle.architecture.equals("moss_tts_nano") || !bundle.backend.equals("cpu")) throw new IOException("当前 MOSS Nano 引擎没有匹配的架构、管线或后端");
        if (!type.equals("speech.synthesize") || !bundle.tasks.equals(Collections.singleton("audio"))) throw new IOException("此 MOSS Nano 配方只提供语音合成");
        Set<String> required = new HashSet<>(JSON); required.addAll(GRAPHS); required.add("text_tokenizer");
        Set<String> filenames = new HashSet<>(); int data = 0;
        for (ModelBundle.Component component : bundle.components) {
            String role = component.role, format = JSON.contains(role) ? "json" : GRAPHS.contains(role) ? "onnx" : role.equals("text_tokenizer") ? "sentencepiece" : role.matches("(?:tts|codec)_data_[1-9][0-9]?") ? "onnx_data" : "";
            if (format.isEmpty() || !format.equals(component.format)) throw new IOException("MOSS Nano 组件角色或格式不匹配：" + role);
            String name = filename(component), group = group(role);
            if (!filenames.add((group + "/" + name).toLowerCase(Locale.ROOT))) throw new IOException("MOSS Nano 组件执行文件名重复");
            if (format.equals("onnx_data") && (!name.endsWith(".data") || ++data > 32)) throw new IOException("外置 ONNX 数据须为显式选择的 .data 文件，最多 32 个");
            if (format.equals("onnx") && (!name.endsWith(".onnx") || component.bytes > 128L * 1024 * 1024)) throw new IOException("ONNX 图须使用外置数据且不超过应用的 128 MiB 图大小保护限制");
            if (format.equals("json") && (!name.endsWith(".json") || component.bytes > 2 * 1024 * 1024)) throw new IOException("MOSS 元数据须为不超过 2 MiB 的 JSON");
            if (format.equals("sentencepiece") && (!name.endsWith(".model") || component.bytes > 16 * 1024 * 1024)) throw new IOException("须选择不超过 16 MiB 的 SentencePiece .model 词表");
            required.remove(role);
        }
        if (!required.isEmpty()) throw new IOException("MOSS Nano 配方缺少必需组件：" + required);
    }
    public static String group(String role) { return role.startsWith("codec_") ? "codec" : "tts"; }
    public static String filename(ModelBundle.Component component) throws IOException {
        return EngineWorkspace.filename(component.path.substring(component.path.lastIndexOf('/') + 1));
    }
    public static JSONObject readMetadata(File file) throws Exception {
        if (file.length() < 1 || file.length() > 2 * 1024 * 1024) throw new IOException("MOSS 元数据大小超过应用限制");
        try (InputStream in = new FileInputStream(file); ByteArrayOutputStream bytes = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192]; int n;
            while ((n = in.read(buffer)) != -1) { if (bytes.size() + n > 2 * 1024 * 1024) throw new IOException("MOSS 元数据大小已改变"); bytes.write(buffer, 0, n); }
            return new JSONObject(new String(bytes.toByteArray(), StandardCharsets.UTF_8));
        }
    }
    public static int voices(JSONObject manifest) throws Exception {
        JSONArray voices = manifest.getJSONArray("builtin_voices");
        if (voices.length() < 1 || voices.length() > 128) throw new IOException("模型须包含 1–128 个用户已下载的音色提示");
        return voices.length();
    }
    public static JSONObject parameters(JSONObject input, int voices) throws Exception {
        if (voices < 1 || voices > 128) throw new IllegalArgumentException("Invalid voice count");
        JSONObject fields = new JSONObject().put("threads", field(2, 1, 16)).put("speaker", field(0, 0, voices - 1))
            .put("maxFrames", field(375, 1, 1500)).put("maxInputTokens", field(1024, 1, 2048)).put("seed", field(1234, 0, Integer.MAX_VALUE));
        return new ParameterSchema(new JSONObject().put("version", 1).put("fields", fields)).normalize(new JSONObject(), input);
    }
    private static JSONObject field(int value, int low, int high) throws Exception { return new JSONObject().put("type", "integer").put("default", value).put("minimum", low).put("maximum", high); }
}
