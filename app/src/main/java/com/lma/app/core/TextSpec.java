package com.lma.app.core;

import org.json.JSONObject;
import java.io.IOException;
import java.util.*;

/** A single user-supplied GGUF and the text-only CPU pipeline contract. */
public final class TextSpec {
    public static final Set<String> FIELDS = Collections.unmodifiableSet(new HashSet<>(Arrays.asList("threads", "context", "maxTokens", "temperature", "reasoning", "systemPrompt")));
    private TextSpec() {}
    public static void validate(ModelBundle bundle, String type) throws Exception {
        if (!type.equals("text.generate") || !bundle.engine.equals("llama_text") || !bundle.backend.equals("cpu") || !bundle.pipeline.equals("text_gguf") || !bundle.tasks.equals(new HashSet<>(Arrays.asList("text")))) throw new IOException("此文本模块只支持 CPU GGUF 生文配方");
        if (bundle.components.size() != 1 || !bundle.components.get(0).role.equals("text_gguf") || !bundle.components.get(0).format.equals("gguf") || AdapterSpec.isAdapter(bundle)) throw new IOException("文本配方需要一个完整 GGUF，不支持拆分权重或外部代码");
        JSONObject fields = bundle.parameters().json().getJSONObject("fields"); Set<String> found = new HashSet<>();
        for (Iterator<String> it = fields.keys(); it.hasNext();) found.add(it.next());
        if (!found.equals(FIELDS)) throw new IOException("文本配方参数必须完整且符合当前基座契约");
        for (String key : FIELDS) {
            String typeName = key.equals("systemPrompt") ? "string" : key.equals("reasoning") ? "enum" : key.equals("temperature") ? "number" : "integer";
            if (!fields.getJSONObject(key).getString("type").equals(typeName)) throw new IOException("文本参数类型与引擎不一致");
        }
        org.json.JSONArray reasoning = fields.getJSONObject("reasoning").getJSONArray("values");
        for (int i = 0; i < reasoning.length(); i++) if (!Arrays.asList("off", "auto", "on").contains(reasoning.getString(i))) throw new IOException("未知文本思考模式");
    }
    public static String prompt(JSONObject input) throws Exception {
        String value = input.getString("prompt");
        if (value.trim().isEmpty() || value.length() > 16000 || value.indexOf('\0') >= 0 || !input.optString("negativePrompt").isEmpty()) throw new IOException("文本生成需要有效提示词，不支持负向提示词");
        return value;
    }
}
