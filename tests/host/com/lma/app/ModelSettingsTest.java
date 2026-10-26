package com.lma.app;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import org.json.*;

/** Binary GGUF fixtures and durable, independent profiles; never runs a model. */
public final class ModelSettingsTest {
    private static final List<String> checks = new ArrayList<>();
    private static void check(boolean value, String name) { if (!value) throw new AssertionError(name); checks.add(name); System.out.println("PASS " + name); }
    private interface Checked { void run() throws Exception; }
    private static void rejects(Checked operation, String name) throws Exception { try { operation.run(); } catch (Exception expected) { check(true, name); return; } throw new AssertionError(name); }
    private static void number(OutputStream out, long value, int width) throws Exception { for (int i = 0; i < width; i++) out.write((int) (value >>> (8 * i)) & 255); }
    private static void string(OutputStream out, String value) throws Exception { byte[] bytes = value.getBytes(StandardCharsets.UTF_8); number(out, bytes.length, 8); out.write(bytes); }
    private static void key(OutputStream out, String name, int type) throws Exception { string(out, name); number(out, type, 4); }
    static byte[] fixture(int version, long context, boolean reversed, int type) throws Exception {
        ByteArrayOutputStream out = new ByteArrayOutputStream(); number(out, 0x46554747, 4); number(out, version, 4); number(out, 0, 8); number(out, 5, 8);
        key(out, "tokenizer.ggml.tokens", 9); number(out, 8, 4); number(out, 2, 8); string(out, "你好"); string(out, "🙂");
        key(out, "tokenizer.ggml.scores", 9); number(out, 6, 4); number(out, 2, 8); number(out, 0, 8);
        key(out, "other.context_length", 4); number(out, 999999, 4);
        if (!reversed) { key(out, "general.architecture", 8); string(out, "qwen3"); }
        key(out, "qwen3.context_length", type); number(out, context, type == 4 || type == 5 ? 4 : 8);
        if (reversed) { key(out, "general.architecture", 8); string(out, "qwen3"); }
        return out.toByteArray();
    }
    public static List<String> run(Path work, Path assets, Path libraries) throws Exception {
        Path folder = work.resolve("model-settings"); Files.createDirectories(folder); Path file = folder.resolve("fixture.gguf");
        Files.write(file, fixture(3, 32768, false, 10)); JSONObject info = GgufMetadata.read(file.toFile());
        check(info.getInt("contextLength") == 32768 && info.getString("architecture").equals("qwen3"), "GGUF uint64 context is read after skipped UTF-8 tokenizer arrays");
        Files.write(file, fixture(2, 4096, true, 4)); check(GgufMetadata.read(file.toFile()).getInt("contextLength") == 4096, "GGUF v2 uint32 context before architecture is resolved without unrelated keys");
        Files.write(file, fixture(3, 16384, false, 11)); check(GgufMetadata.read(file.toFile()).getInt("contextLength") == 16384, "GGUF int64 context metadata is supported");
        byte[] truncated = fixture(3, 4096, false, 4); Files.write(file, Arrays.copyOf(truncated, truncated.length - 2)); rejects(() -> GgufMetadata.read(file.toFile()), "Truncated GGUF metadata fails without allocating tensor data");
        ByteArrayOutputStream malformed = new ByteArrayOutputStream(); number(malformed, 0x46554747, 4); number(malformed, 3, 4); number(malformed, 0, 8); number(malformed, 1, 8); key(malformed, "tokenizer.ggml.tokens", 9); number(malformed, 8, 4); number(malformed, Long.MAX_VALUE, 8);
        Files.write(file, malformed.toByteArray()); rejects(() -> GgufMetadata.read(file.toFile()), "Untrusted GGUF array count is bounded before allocation or iteration");
        Files.write(file, fixture(3, Long.MAX_VALUE, false, 10)); check(GgufMetadata.read(file.toFile()).optString("source").equals("unknown"), "Unrepresentable context bounds are explicitly unknown");
        JSONObject small = new JSONObject().put("contextLength", 4096), defaults = ModelSettings.defaults();
        JSONObject capped = ModelSettings.normalize(defaults, new JSONObject().put("context", "999999999999999999").put("maxTokens", 99999).put("threads", 999999).put("temperature", 5), small);
        check(capped.getInt("context") == 4096 && capped.getInt("maxTokens") == 4095, "Oversized editable context and output values clamp to the model and shared context limits");
        check(capped.getInt("threads") == Runtime.getRuntime().availableProcessors() && capped.getDouble("temperature") == 2, "Device thread and application temperature bounds are distinguished from model metadata");
        JSONObject reduced = ModelSettings.normalize(capped, new JSONObject().put("context", 300.9).put("maxTokens", 800), small);
        check(reduced.getInt("context") == 300 && reduced.getInt("maxTokens") == 299, "Reducing context clamps its output limit and normalizes integer fields");
        JSONObject lower = ModelSettings.normalize(defaults, new JSONObject().put("context", -1).put("maxTokens", -1).put("temperature", -1).put("threads", 0), small);
        check(lower.getInt("context") == 2 && lower.getInt("maxTokens") == 1 && lower.getInt("threads") == 1 && lower.getDouble("temperature") == 0, "Numeric lower bounds remain usable");
        check(!ModelSettings.limits(new JSONObject(), 2048).getBoolean("contextKnown") && ModelSettings.limits(new JSONObject(), 2048).getInt("contextMax") == 8192, "Absent model metadata uses an explicitly labeled application fallback");
        rejects(() -> ModelSettings.normalize(defaults, new JSONObject().put("context", "NaN"), small), "Native numeric validation rejects non-finite editable text");
        rejects(() -> ModelSettings.normalize(defaults, new JSONObject().put("context", ""), small), "Native numeric validation rejects empty editable text");
        rejects(() -> ModelSettings.normalize(defaults, new JSONObject().put("reasoning", "invalid"), small), "Per-model reasoning modes are validated");
        rejects(() -> ModelSettings.normalize(defaults, new JSONObject().put("systemPrompt", String.join("", Collections.nCopies(4001, "x"))), small), "Per-model system prompt length is bounded");
        check(ModelSettings.reload(defaults, capped) && !ModelSettings.reload(defaults, ModelSettings.normalize(defaults, new JSONObject().put("temperature", 1.2).put("maxTokens", 77).put("systemPrompt", "new"), small)), "Only context, threads and reasoning require an engine reload");
        LmaApp app = new LmaApp(folder.resolve("state").toFile(), assets.toFile(), libraries.toFile());
        Files.write(app.store.modelFile("m08").toPath(), fixture(3, 4096, false, 10)); app.store.inspectModel("m08");
        app.store.saveConfig("m08", new JSONObject().put("context", 90000).put("maxTokens", 90000).put("systemPrompt", "profile A").put("temperature", 1.3));
        app.store.saveConfig("m06", new JSONObject().put("context", 777).put("systemPrompt", "profile B"));
        check(app.settings("m08").getInt("context") == 4096 && app.settings("m08").getInt("maxTokens") == 4095 && app.settings("m06").getInt("context") == 777, "Production Store profiles keep separate model context and output settings");
        check(app.settings("m08").getString("systemPrompt").equals("profile A") && app.settings("m06").getString("systemPrompt").equals("profile B"), "System prompts and generation preferences follow the selected model");
        Store restarted = new Store(app); check(restarted.config("m08").getJSONObject("values").getDouble("temperature") == 1.3 && restarted.config("m06").getJSONObject("values").getInt("context") == 777, "Atomic model profiles survive Store reconstruction");
        Files.write(app.store.modelFile("m08").toPath(), fixture(3, 1024, true, 4)); Files.setLastModifiedTime(app.store.modelFile("m08").toPath(), java.nio.file.attribute.FileTime.fromMillis(System.currentTimeMillis() + 5000));
        JSONObject inspected = app.store.inspectModel("m08"); check(inspected.getJSONObject("values").getInt("context") == 1024 && inspected.getJSONObject("values").getInt("maxTokens") == 1023, "Changed GGUF files invalidate cached bounds and normalize the saved profile");
        String imported = app.store.addCustom("legacy import", "", "", true);
        app.prefs.edit().putInt("context", 3000).putInt("maxTokens", 333).putString("systemPrompt", "legacy value").apply();
        Store migrated = new Store(app); check(migrated.config(imported).getJSONObject("values").getInt("context") == 3000 && migrated.config(imported).getJSONObject("values").getInt("maxTokens") == 333 && migrated.config("m06").getJSONObject("values").getInt("context") == 777, "Legacy global preferences migrate once without overwriting existing model profiles");
        check(app.prefs.getInt("context", -1) == -1, "Legacy global inference preference keys are removed after durable migration");
        String fresh = migrated.addCustom("new import", "", "", true); check(migrated.config(fresh).getJSONObject("values").getInt("context") == 2048, "New imported models start with independent defaults");
        Files.write(app.store.modelFile(imported).toPath(), new byte[24]); check(migrated.inspectModel(imported).getJSONObject("limits").getBoolean("contextKnown") == false, "Invalid model metadata stays unknown without blocking parameter management");
        app.engineModel = imported; app.engineState = "stopped"; migrated.remove(imported); check(app.engineModel.isEmpty(), "Deleting a stopped selected custom model clears its stale selection");
        app.store.remove("m08"); check(app.store.config("m08").getJSONObject("values").getString("systemPrompt").equals("profile A"), "Deleting curated weights preserves their independent settings for redownload");
        return checks;
    }
}
