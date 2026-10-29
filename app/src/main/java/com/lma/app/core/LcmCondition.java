package com.lma.app.core;

import org.json.JSONObject;
import java.io.*;
import java.nio.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Bounded, source-bound data overlay; it supplies no executable code or fallback weights. */
public final class LcmCondition {
    private LcmCondition() {}
    public static final String ROLE = "condition_bias", SCHEMA = "lma.condition-bias-overlay/1";
    private static final String ALGORITHM = "lcm-fixed-guidance-f16-mlp-double-dot/1";
    public static JSONObject descriptor(ModelBundle bundle) throws Exception {
        boolean present = false; for (ModelBundle.Component c : bundle.components) present |= c.role.equals(ROLE);
        JSONObject value = bundle.json().optJSONObject("conditionBias");
        if (!present && value == null) return null;
        if (!present || value == null) throw new IOException("LCM 条件组件和来源绑定必须同时声明");
        Set<String> fields = new HashSet<>(Arrays.asList("schema", "algorithm", "sourceSha256", "baseSha256", "distilledGuidance"));
        if (value.length() != fields.size()) throw new IOException("未知的 LCM 条件组件字段");
        for (Iterator<String> it = value.keys(); it.hasNext();) if (!fields.contains(it.next())) throw new IOException("未知的 LCM 条件组件字段");
        if (!SCHEMA.equals(value.getString("schema")) || !ALGORITHM.equals(value.getString("algorithm"))
                || !Protocol.isSha256(value.getString("sourceSha256")) || !Protocol.isSha256(value.getString("baseSha256"))
                || !(value.get("distilledGuidance") instanceof Number) || value.getDouble("distilledGuidance") != 8.5) throw new IOException("未知的 LCM 条件组件来源或固定 guidance 合约");
        Set<String> roles = new HashSet<>(); for (ModelBundle.Component c : bundle.components) roles.add(c.role);
        if (!bundle.engine.equals("sd_cpp") || !bundle.pipeline.equals("sd15_lcm") || !bundle.architecture.equals("sd15")
                || !roles.equals(new HashSet<>(Arrays.asList("model", "clip_merges", ROLE)))
                || !bundle.component(ROLE).format.equals("gguf") || bundle.component(ROLE).bytes < 5120 || bundle.component(ROLE).bytes > 65536
                || !bundle.component("model").format.equals("gguf") || !bundle.component("model").sha256.equals(value.getString("baseSha256"))) throw new IOException("LCM 条件组件必须绑定匹配的 SD1.5 完整基础模型");
        return DataFiles.copy(value);
    }
    public static JSONObject verify(ModelBundle bundle, File file) throws Exception {
        JSONObject descriptor = descriptor(bundle); if (descriptor == null) throw new IOException("此模型未声明条件组件");
        ModelBundle.Component component = bundle.component(ROLE);
        if (!file.isFile() || file.length() != component.bytes || !DataFiles.sha256(file).equals(component.sha256)) throw new IOException("LCM 条件组件文件已改变");
        byte[] data = new byte[(int) component.bytes];
        try (DataInputStream in = new DataInputStream(new FileInputStream(file))) { in.readFully(data); if (in.read() != -1) throw new IOException("LCM 条件文件长度已改变"); }
        try {
            ByteBuffer bytes = ByteBuffer.wrap(data).order(ByteOrder.LITTLE_ENDIAN);
            if (bytes.getInt() != 0x46554747 || bytes.getInt() != 3 || bytes.getLong() != 1 || bytes.getLong() != 6) throw new IOException("LCM 条件文件必须恰好包含一个 GGUFv3 张量与完整来源元数据");
            Map<String,String> metadata = new HashMap<>();
            for (int i = 0; i < 6; i++) { String key = string(bytes); if (bytes.getInt() != 8 || metadata.put(key, string(bytes)) != null) throw new IOException("LCM 条件元数据重复或类型错误"); }
            Map<String,String> expected = new HashMap<>();
            expected.put("lma.overlay.schema", SCHEMA); expected.put("lma.overlay.algorithm", descriptor.getString("algorithm"));
            expected.put("lma.overlay.source_sha256", descriptor.getString("sourceSha256")); expected.put("lma.overlay.base_sha256", descriptor.getString("baseSha256"));
            expected.put("lma.overlay.distilled_guidance", "8.5"); expected.put("lma.overlay.sampler_cfg", "1");
            if (!metadata.equals(expected) || !string(bytes).equals("model.diffusion_model.time_embed.0.bias") || bytes.getInt() != 1
                    || bytes.getLong() != 1280 || bytes.getInt() != 0 || bytes.getLong() != 0) throw new IOException("LCM 条件张量、来源或基础模型不匹配");
            while (bytes.position() % 32 != 0) if (bytes.get() != 0) throw new IOException("LCM 条件填充非法");
            if (bytes.remaining() != 5120) throw new IOException("LCM 条件数据大小不匹配");
            while (bytes.hasRemaining()) if (!Float.isFinite(bytes.getFloat())) throw new IOException("LCM 条件数据包含非有限数值");
        } catch (BufferUnderflowException | IndexOutOfBoundsException error) { throw new IOException("LCM 条件文件被截断", error); }
        return descriptor;
    }
    private static String string(ByteBuffer bytes) throws IOException {
        long length = bytes.getLong(); if (length < 1 || length > 512 || length > bytes.remaining()) throw new IOException("LCM 条件字符串超出边界");
        byte[] value = new byte[(int) length]; bytes.get(value); for (byte c : value) if (c < 32 || c > 126) throw new IOException("LCM 条件元数据必须为有效 ASCII");
        return new String(value, StandardCharsets.US_ASCII);
    }
}
