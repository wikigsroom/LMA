package com.lma.app;

import com.lma.app.core.*;
import org.json.JSONObject;
import java.io.File;

/** Internal signed-App module contract, implemented by each actual local runtime. */
public interface LocalEngine {
    String id();
    JSONObject describe() throws Exception;
    void validate(ModelBundle bundle, String type) throws Exception;
    File generate(Context context) throws Exception;
    interface Context {
        BundleStore.Lease model();
        JSONObject request();
        File output(String suffix) throws Exception;
        void check() throws Exception;
        void progress(String stage, Double fraction) throws Exception;
        void process(Process process) throws Exception;
        void execution(JSONObject details) throws Exception;
    }
}
