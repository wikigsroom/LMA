package com.lma.app.core;

import java.io.*;
import java.nio.charset.StandardCharsets;
import org.json.*;

/** Bounded GLB 2.0 inspection; reject external resources before preview or export. */
public final class GlbFile {
    public static final String MIME="model/gltf-binary";
    private GlbFile() {}
    private static long u32(RandomAccessFile in) throws IOException {
        return Integer.toUnsignedLong(Integer.reverseBytes(in.readInt()));
    }
    public static JSONObject inspect(File file) throws Exception {
        try(RandomAccessFile in=new RandomAccessFile(file,"r")) {
            long length=in.length();
            if(length<28 || length>8L*1024*1024*1024 || u32(in)!=0x46546c67L || u32(in)!=2 || u32(in)!=length)throw new IOException("无效或不完整的 GLB 2.0 文件");
            long jsonLength=u32(in);
            if(jsonLength<2 || jsonLength>8*1024*1024 || jsonLength%4!=0 || u32(in)!=0x4e4f534aL || 20+jsonLength+8>length)throw new IOException("GLB JSON 块超出范围");
            byte[] bytes=new byte[(int)jsonLength];in.readFully(bytes);JSONObject gltf=new JSONObject(new String(bytes,StandardCharsets.UTF_8));
            long binLength=u32(in);
            if(u32(in)!=0x004e4942L || binLength%4!=0 || in.getFilePointer()+binLength!=length)throw new IOException("GLB 二进制块不完整");
            if(!gltf.getJSONObject("asset").getString("version").equals("2.0"))throw new IOException("只接受 glTF 2.0");
            JSONArray buffers=gltf.getJSONArray("buffers"), views=gltf.getJSONArray("bufferViews"), accessors=gltf.getJSONArray("accessors"), meshes=gltf.getJSONArray("meshes");
            if(buffers.length()!=1 || buffers.getJSONObject(0).has("uri") || buffers.getJSONObject(0).getLong("byteLength")<1 ||
               buffers.getJSONObject(0).getLong("byteLength")>binLength || views.length()>8192 || accessors.length()>8192 || meshes.length()<1 || meshes.length()>1024)throw new IOException("GLB 资源范围无效");
            long usable=buffers.getJSONObject(0).getLong("byteLength");
            for(int i=0;i<views.length();i++) {
                JSONObject v=views.getJSONObject(i);long offset=v.optLong("byteOffset",0), size=v.getLong("byteLength");
                if(v.getInt("buffer")!=0 || offset<0 || size<1 || offset>usable || size>usable-offset)throw new IOException("GLB 视图越界");
                if(v.has("byteStride") && (v.getInt("byteStride")<4 || v.getInt("byteStride")>252 || v.getInt("byteStride")%4!=0))throw new IOException("GLB 步长无效");
            }
            for(int i=0;i<accessors.length();i++) {
                JSONObject a=accessors.getJSONObject(i);int index=a.getInt("bufferView"), code=a.getInt("componentType");
                if(index<0 || index>=views.length() || a.has("sparse"))throw new IOException("GLB accessor 不受支持");
                int unit=code==5126||code==5125?4:code==5123||code==5122?2:code==5120||code==5121?1:0;
                String type=a.getString("type");int width=type.equals("SCALAR")?1:type.equals("VEC2")?2:type.equals("VEC3")?3:type.equals("VEC4")?4:0;
                long count=a.getLong("count"), offset=a.optLong("byteOffset",0);JSONObject view=views.getJSONObject(index);
                int stride=view.optInt("byteStride",unit*width);
                if(unit==0||width==0||count<1||count>10000000||offset<0||offset%unit!=0||stride<unit*width||
                   offset>view.getLong("byteLength")||Math.addExact(Math.multiplyExact(count-1,stride),unit*width)>view.getLong("byteLength")-offset)throw new IOException("GLB accessor 越界");
            }
            long vertices=0,triangles=0;
            for(int i=0;i<meshes.length();i++) {
                JSONArray primitives=meshes.getJSONObject(i).getJSONArray("primitives");
                if(primitives.length()>1024)throw new IOException("GLB 图元数量超出范围");
                for(int j=0;j<primitives.length();j++) {
                    JSONObject p=primitives.getJSONObject(j);if(p.optInt("mode",4)!=4 || p.has("extensions"))throw new IOException("只接受未压缩三角网格");
                    int position=p.getJSONObject("attributes").getInt("POSITION");
                    JSONObject a=accessors.getJSONObject(position);if(!a.getString("type").equals("VEC3")||a.getInt("componentType")!=5126)throw new IOException("GLB 顶点格式无效");
                    vertices+=a.getLong("count");long indices=a.getLong("count");
                    if(p.has("indices")) {
                        JSONObject index=accessors.getJSONObject(p.getInt("indices"));
                        if(!index.getString("type").equals("SCALAR") || !java.util.Arrays.asList(5121,5123,5125).contains(index.getInt("componentType")))throw new IOException("GLB 索引格式无效");
                        indices=index.getLong("count");
                    }
                    if(indices%3!=0)throw new IOException("GLB 三角形索引不完整");triangles+=indices/3;
                }
            }
            JSONArray images=gltf.optJSONArray("images");
            if(images!=null)for(int i=0;i<images.length();i++) {
                JSONObject image=images.getJSONObject(i);int view=image.getInt("bufferView");
                if(image.has("uri")||view<0||view>=views.length()||!java.util.Arrays.asList("image/png","image/jpeg").contains(image.getString("mimeType")))throw new IOException("GLB 不允许外部或未知贴图");
            }
            return new JSONObject().put("mime",MIME).put("format","glTF 2.0").put("meshes",meshes.length()).put("vertices",vertices)
                .put("triangles",triangles).put("textures",images==null?0:images.length()).put("selfContained",true);
        }
    }
}
