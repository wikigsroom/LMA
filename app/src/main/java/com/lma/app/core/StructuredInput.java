package com.lma.app.core;

import org.json.JSONObject;
import java.io.*;
import java.nio.charset.*;
import java.nio.file.Files;
import java.util.*;

/** Typed local data inputs. Arbitrary JSON and generated-text envelopes are not input data. */
public final class StructuredInput {
    public static final String MIME = "application/vnd.lma.data+json";
    public static final int MAX_BYTES = 8 * 1024 * 1024;
    private StructuredInput() {}
    public static boolean looksJson(File file) throws IOException {
        try (InputStream in = new FileInputStream(file)) {
            for (int i=0;i<4096;i++) { int c=in.read(); if(c<0)return false; if(c==' '||c=='\r'||c=='\n'||c=='\t')continue; return c=='{'; }
            return false;
        }
    }
    public static JSONObject read(File file) throws Exception {
        if(!file.isFile()||Files.isSymbolicLink(file.toPath())||file.length()<2||file.length()>MAX_BYTES)throw new IOException("本地数据 JSON 不存在或超过 8 MiB");
        String text=StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT).decode(java.nio.ByteBuffer.wrap(Files.readAllBytes(file.toPath()))).toString();
        int depth=0;boolean quoted=false,escaped=false;for(int i=0;i<text.length();i++){char c=text.charAt(i);if(quoted){if(escaped)escaped=false;else if(c=='\\')escaped=true;else if(c=='"')quoted=false;}else if(c=='"')quoted=true;else if(c=='{'||c=='['){if(++depth>12)throw new IOException("本地 JSON 嵌套超限");}else if(c=='}'||c==']'){if(--depth<0)throw new IOException("本地 JSON 格式无效");}}
        org.json.JSONTokener tokener=new org.json.JSONTokener(text);JSONObject value=new JSONObject(tokener);if(tokener.nextClean()!=0)throw new IOException("JSON 后存在额外内容");return value;
    }
    public static JSONObject inspectDocument(File file) throws Exception {
        JSONObject value=read(file);String type=value.getString("schema");
        if(type.equals("lma.text-result/1"))return TextResult.inspect(file);
        return inspect(file,value);
    }
    public static JSONObject inspect(File file) throws Exception { return inspect(file,read(file)); }
    private static JSONObject inspect(File file,JSONObject value) throws Exception {
        String type=value.getString("schema");JSONObject metadata=new JSONObject().put("mime",MIME).put("dataType",type);
        if(type.equals("lma.pointcloud/1")) { PointCloudSpec.reference(file);return metadata.put("points",value.getJSONArray("points").length()); }
        if(type.equals("lma.camera/1")) {
            for(Iterator<String> it=value.keys();it.hasNext();)if(!Arrays.asList("schema","extrinsic","intrinsic","projection_intrinsic","distance","camera_angle_x","mesh_scale").contains(it.next()))throw new IOException("未知相机数据字段");
            SupraSpec.camera(file);return metadata;
        }
        throw new IOException("请选择 lma.camera/1 或 lma.pointcloud/1 格式；不接受任意 JSON");
    }
}
