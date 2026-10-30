package com.lma.app;

import com.lma.app.core.DataFiles;
import java.io.*;
import java.util.*;
import java.util.concurrent.TimeUnit;
import org.json.*;

/** Windows evidence port only. The APK keeps the production Android MediaCodec implementation. */
public final class VideoEncoder {
    static final JSONArray receipts = new JSONArray();
    static final Map<String, JSONObject> metadata = new HashMap<>();
    private static int integer(DataInputStream in) throws IOException { return Integer.reverseBytes(in.readInt()); }
    public static void encode(File raw, File output, DataFiles.Check check) throws Exception {
        String ffmpeg = System.getProperty("lma.host.ffmpeg");
        if (ffmpeg == null || !new File(ffmpeg).isFile()) throw new IOException("Explicit native host encoder is missing");
        Process child = null;
        try (DataInputStream in = new DataInputStream(new BufferedInputStream(new FileInputStream(raw)))) {
            byte[] magic = new byte[8]; in.readFully(magic);
            if (!Arrays.equals(magic, new byte[]{'L','M','A','F','R','M','1',0})) throw new IOException("Invalid real frame header");
            int width=integer(in), height=integer(in), count=integer(in), fps=integer(in), channels=integer(in);
            if (width<64 || width>2048 || height<64 || height>2048 || width%2!=0 || height%2!=0 || count<2 || count>129 || fps<1 || fps>60 || channels!=3 || raw.length()!=28L+width*(long)height*3*count) throw new IOException("Invalid real frame geometry");
            File log = new File(output.getPath()+".host-encoder.log");
            child = new ProcessBuilder(ffmpeg,"-hide_banner","-loglevel","error","-y","-f","rawvideo","-pixel_format","rgb24","-video_size",width+"x"+height,
                "-framerate",String.valueOf(fps),"-i","pipe:0","-frames:v",String.valueOf(count),"-an","-c:v","libx264","-threads","2","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart",output.getPath())
                .redirectErrorStream(true).redirectOutput(log).start();
            boolean moving=false; byte[] pixels=new byte[width*height*3], first=null;
            try (OutputStream input = new BufferedOutputStream(child.getOutputStream())) {
                for(int frame=0;frame<count;frame++) {
                    check.run(); in.readFully(pixels);
                    if(first==null)first=pixels.clone();else if(!Arrays.equals(first,pixels))moving=true;
                    input.write(pixels);
                }
            }
            if(!child.waitFor(120,TimeUnit.SECONDS))throw new IOException("Owned host encoder timed out");
            if(child.exitValue()!=0 || !output.isFile() || output.length()<32)throw new IOException("Actual host encoding failed");
            if(!moving)throw new IOException("Generated video contains only repeated static frames");
            check.run();
            JSONObject record=new JSONObject().put("input_raw_sha256",DataFiles.sha256(raw)).put("input_raw_bytes",raw.length())
                .put("width",width).put("height",height).put("frames",count).put("fps",fps).put("motion_observed",true)
                .put("output_sha256",DataFiles.sha256(output)).put("output_bytes",output.length()).put("output",output.getPath())
                .put("encoder","native_windows_ffmpeg_libx264").put("android_codec_tested",false);
            receipts.put(record); metadata.put(output.getCanonicalPath(),record);
        } finally {
            if(child!=null && child.isAlive()){child.destroyForcibly();child.waitFor(10,TimeUnit.SECONDS);}
        }
    }
    static JSONObject inspect(File file) throws Exception {
        JSONObject record=metadata.get(file.getCanonicalPath());
        if(record==null || !DataFiles.sha256(file).equals(record.getString("output_sha256")))throw new IOException("Unknown actual encoded output");
        return new JSONObject().put("mime","video/mp4").put("width",record.getInt("width")).put("height",record.getInt("height"))
            .put("durationMs",record.getInt("frames")*1000L/record.getInt("fps"));
    }
}
