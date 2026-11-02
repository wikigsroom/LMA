package com.lma.app;
import android.graphics.*;
import android.media.MediaMetadataRetriever;
import android.util.Base64;
import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.util.*;

/** Bounded image preprocessing and timestamped video-frame composition, on the same phone. */
public final class VisionInputs {
    private VisionInputs(){}
    public static void validate(LmaApp app,String model,JSONArray ids)throws Exception{
        if(ids.length()<1||ids.length()>4)throw new IllegalArgumentException("一次理解选择 1–4 份图片 / 视频");
        JSONObject pair=app.visionPairs==null?null:app.visionPairs.pair(model);if(pair==null||!app.bundles.plan(pair.getString("bundleId")).getBoolean("installed"))throw new IllegalArgumentException("当前模型没有已核对并完整安装的视觉组件；请改选模型或管理视觉配对");
        for(int i=0;i<ids.length();i++){JSONObject a=app.artifacts.get(ids.getString(i)),m=a.getJSONObject("metadata");String mime=m.getString("mime");if(!mime.startsWith("image/")&&!mime.equals("video/mp4"))throw new IllegalArgumentException("此桥不支持原生音频、转写或 3D 理解，请改选已适配路线");if(mime.equals("video/mp4")&&m.optLong("durationMs")>30000)throw new IllegalArgumentException("抽帧理解限 30 秒视频，请明确裁剪输入");}
    }
    public static Prepared prepare(LmaApp app,String model,JSONArray ids,int context,DataFiles.Check check)throws Exception{
        validate(app,model,ids);Prepared result=new Prepared();int budget=Math.min(4,Math.max(0,(context-1024)/1024));if(budget<1)throw new IOException("视觉上下文预算不足，请为此模型设置至少 2048 上下文");
        int count=0;
        try{for(int i=0;i<ids.length();i++){check.run();ArtifactStore.Lease lease=app.artifacts.acquire(ids.getString(i));result.leases.add(lease);JSONObject record=app.artifacts.get(ids.getString(i));if(!DataFiles.sha256(lease.file,check).equals(record.getString("sha256")))throw new IOException("视觉素材哈希不符，请重新导入");String mime=record.getJSONObject("metadata").getString("mime");
            if(mime.startsWith("image/")){if(++count>budget)throw new IOException("图片 / 帧数量超出此模型的视觉 token 保守预算");BitmapFactory.Options bounds=new BitmapFactory.Options();bounds.inJustDecodeBounds=true;BitmapFactory.decodeFile(lease.file.getPath(),bounds);if(bounds.outWidth<1||bounds.outHeight<1||bounds.outWidth*(long)bounds.outHeight>4096L*4096)throw new IOException("图片损坏或超过解码预算");BitmapFactory.Options options=new BitmapFactory.Options();options.inSampleSize=Math.max(1,Math.max(bounds.outWidth,bounds.outHeight)/768);Bitmap bitmap=BitmapFactory.decodeFile(lease.file.getPath(),options);if(bitmap==null)throw new IOException("图片无法解码");try{result.image(bitmap,check);}finally{bitmap.recycle();}}
            else {MediaMetadataRetriever retriever=new MediaMetadataRetriever();try{retriever.setDataSource(lease.file.getPath());long duration=record.getJSONObject("metadata").getLong("durationMs");int frames=Math.min(3,budget-count);if(frames<1)throw new IOException("没有可用的视频抽帧预算");for(int f=0;f<frames;f++){check.run();long timestamp=frames==1?0:f*duration*1000/(frames-1);timestamp=Math.min(timestamp,Math.max(0,duration*1000-1000));Bitmap frame=retriever.getScaledFrameAtTime(timestamp,MediaMetadataRetriever.OPTION_CLOSEST,768,768);if(frame==null)throw new IOException("视频帧无法解码");result.content.put(new JSONObject().put("type","text").put("text","[Local sampled video frame @ "+(timestamp/1000)+" ms; composed image input, not native video processing]"));try{result.image(frame,check);}finally{frame.recycle();}count++;}}finally{retriever.release();}}
        }return result;}catch(Exception error){result.close();throw error;}
    }
    public static final class Prepared implements AutoCloseable {
        public final JSONArray content=new JSONArray();private final List<ArtifactStore.Lease> leases=new ArrayList<>();private int bytes;
        private void image(Bitmap bitmap,DataFiles.Check check)throws Exception{check.run();double scale=Math.min(1,768.0/Math.max(bitmap.getWidth(),bitmap.getHeight()));Bitmap scaled=Bitmap.createScaledBitmap(bitmap,Math.max(1,(int)(bitmap.getWidth()*scale)),Math.max(1,(int)(bitmap.getHeight()*scale)),true);try(ByteArrayOutputStream out=new ByteArrayOutputStream()){if(!scaled.compress(Bitmap.CompressFormat.JPEG,85,out))throw new IOException("图片预处理失败");bytes+=out.size();if(bytes>4*1024*1024)throw new IOException("视觉输入超过 4 MiB 请求预算");content.put(new JSONObject().put("type","image_url").put("image_url",new JSONObject().put("url","data:image/jpeg;base64,"+Base64.encodeToString(out.toByteArray(),Base64.NO_WRAP))));}finally{if(scaled!=bitmap)scaled.recycle();}check.run();}
        @Override public void close(){for(ArtifactStore.Lease lease:leases)lease.close();leases.clear();}
    }
}
