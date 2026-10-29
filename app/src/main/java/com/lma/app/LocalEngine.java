package com.lma.app;

import com.lma.app.core.*;
import org.json.JSONObject;
import java.io.File;

/** Internal signed-App module contract, implemented by each actual local runtime. */
public interface LocalEngine {
    String id();
    JSONObject describe() throws Exception;
    void validate(ModelBundle bundle, String type) throws Exception;
    default InputSpec inputs(ModelBundle bundle, String type) throws Exception { return InputSpec.promptOnly(); }
    default JSONObject prepare(ModelBundle bundle, JSONObject request) throws Exception { return request; }
    File generate(Context context) throws Exception;
    interface Context {
        BundleStore.Lease model();
        default java.util.List<BundleStore.Lease> adapters() { return java.util.Collections.emptyList(); }
        JSONObject request();
        default File input(String role) throws Exception { throw new java.io.IOException("This context has no selected local input: " + role); }
        File output(String suffix) throws Exception;
        void check() throws Exception;
        void progress(String stage, Double fraction) throws Exception;
        void process(Process process) throws Exception;
        void execution(JSONObject details) throws Exception;
        default boolean audioStreaming() { return false; }
        default void audioStart(AudioPcm.Format format) throws Exception { throw new java.io.IOException("Audio previews are unavailable in this context"); }
        default void audioChunk(AudioPcm.Chunk chunk) throws Exception { throw new java.io.IOException("Audio previews are unavailable in this context"); }
    }
}
