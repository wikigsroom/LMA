package com.lma.app;
import org.json.*;import com.lma.app.core.DataFiles;
/** Legacy gateway host scope excludes Android Bitmap/MediaMetadataRetriever. */
public final class VisionInputs {
    public static void validate(LmaApp app,String id,JSONArray refs)throws Exception{if(refs.length()>0)throw new java.io.IOException("Android visual input is not available in this host port");}
    public static Prepared prepare(LmaApp app,String id,JSONArray refs,int context,DataFiles.Check check)throws Exception{validate(app,id,refs);return new Prepared();}
    public static final class Prepared implements AutoCloseable{public final JSONArray content=new JSONArray();public void close(){}}
}
