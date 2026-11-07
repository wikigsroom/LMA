package com.lma.app;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Intent;
import android.os.Bundle;
import java.io.RandomAccessFile;
import java.lang.reflect.Method;
import org.json.JSONArray;
import org.json.JSONObject;

/** Read-only whitelist of installed m04 positional/context metadata; no tensor data, vocabulary or credentials. */
public final class DeviceM04Metadata extends Instrumentation {
    private Method number, string, skip;
    @Override public void onCreate(Bundle args) { super.onCreate(args); start(); }
    private long num(RandomAccessFile f, int bytes) throws Exception { return (Long)number.invoke(null, f, bytes); }
    private String str(RandomAccessFile f, int limit) throws Exception { return (String)string.invoke(null, f, limit); }
    @Override public void onStart() {
        JSONObject result = new JSONObject();
        try {
            LmaApp app = (LmaApp)getTargetContext().getApplicationContext();
            startActivitySync(new Intent(getTargetContext(), MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            long startup = System.nanoTime() + java.util.concurrent.TimeUnit.SECONDS.toNanos(60);
            while (app.store == null && System.nanoTime() < startup) Thread.sleep(100);
            if (app.store == null) throw new IllegalStateException("Application store initialization did not finish");
            number = GgufMetadata.class.getDeclaredMethod("number", RandomAccessFile.class, int.class);
            string = GgufMetadata.class.getDeclaredMethod("string", RandomAccessFile.class, int.class);
            skip = GgufMetadata.class.getDeclaredMethod("skipValue", RandomAccessFile.class, int.class);
            number.setAccessible(true); string.setAccessible(true); skip.setAccessible(true);
            JSONObject values = new JSONObject(); JSONArray positional = new JSONArray();
            try (RandomAccessFile f = new RandomAccessFile(app.store.modelFile("m04"), "r")) {
                if (num(f, 4) != 0x46554747L) throw new IllegalStateException("GGUF required");
                long version = num(f, 4), tensors = num(f, 8), count = num(f, 8);
                if ((version != 2 && version != 3) || count > 100000 || tensors > 100000) throw new IllegalStateException("Bounded GGUF v2/v3 required");
                for (long i = 0; i < count; i++) {
                    String key = str(f, 1024); int type = (int)num(f, 4);
                    boolean wanted = key.startsWith("llama.") || key.equals("general.architecture") || key.equals("tokenizer.ggml.add_bos_token") || key.equals("tokenizer.ggml.add_eos_token");
                    if (!wanted || type == 9) { skip.invoke(null, f, type); continue; }
                    Object value;
                    if (type == 8) value = str(f, 1024);
                    else if (type == 7) value = num(f, 1) != 0;
                    else if (type == 6) value = Float.intBitsToFloat((int)num(f, 4));
                    else if (type == 12) value = Double.longBitsToDouble(num(f, 8));
                    else value = num(f, type <= 1 ? 1 : type <= 3 ? 2 : type <= 5 ? 4 : 8);
                    values.put(key, value);
                }
                for (long i = 0; i < tensors; i++) {
                    String name = str(f, 1024); int dims = (int)num(f, 4);
                    if (dims < 1 || dims > 4) throw new IllegalStateException("Invalid tensor dimensions");
                    JSONArray shape = new JSONArray(); for (int j = 0; j < dims; j++) shape.put(num(f, 8));
                    long type = num(f, 4); num(f, 8);
                    if (name.contains("rope_freq")) positional.put(new JSONObject().put("name", name).put("shape", shape).put("ggmlType", type));
                }
                result.put("headerBytesInspected", f.getFilePointer());
            }
            JSONObject saved = app.settings("m04"), settings = new JSONObject();
            for (String key : new String[]{"context", "maxTokens", "threads", "temperature", "reasoning"})
                settings.put(key, saved.get(key));
            result.put("status", "passed").put("metadata", values).put("positionalTensors", positional)
                .put("savedSettings", settings).put("tensorDataRead", false).put("modelModified", false);
        } catch (Throwable error) {
            try { result.put("status", "failed").put("error", error.getClass().getSimpleName()); } catch (Exception ignored) { }
        }
        Bundle out = new Bundle(); out.putString("lma_m04_metadata", result.toString()); finish(Activity.RESULT_OK, out);
    }
}
