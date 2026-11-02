package com.lma.app;

import android.graphics.*;
import android.media.*;
import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.*;
import java.util.*;

/** Same-phone AVC/AAC composition. Original video audio is replaced, not silently mixed. */
public final class MediaComposer {
    private MediaComposer() {}
    public static JSONObject freeze(LmaApp app,JSONObject raw) throws Exception {
        JSONObject request=CompositionSpec.validate(raw); request=InputSelection.prepare(app.artifacts,CompositionSpec.inputs(),request);
        JSONObject p=request.getJSONObject("parameters"); JSONArray refs=request.getJSONArray("inputReceipts");
        for(int i=0;i<refs.length();i++) {JSONObject r=refs.getJSONObject(i),m=r.getJSONObject("metadata");if(!r.getString("role").equals("visual"))continue;
            if(m.getString("mime").startsWith("image/")&&p.getDouble("durationSeconds")>15)throw new IOException("静态图片成片限 15 秒，请缩短时长");
            if(m.getString("mime").equals("video/mp4")&&m.optLong("durationMs")<Math.round(p.getDouble("durationSeconds")*1000))throw new IOException("原视频比成片时长短；请缩短成片，不循环或补帧");
        }
        return request.put("composition",new JSONObject().put("audioPolicy","replace_original_mix_wav_trim_or_silence_pad").put("imagePolicy","explicit_still_presentation_not_generated_motion").put("execution","same_android_phone"));
    }
    public static File generate(LmaApp app,JSONObject request,String id,DataFiles.Check check) throws Exception {
        try(InputSelection.Selection input=InputSelection.acquire(app.artifacts,CompositionSpec.inputs(),request,check);PcmMixer mixer=new PcmMixer()) {
            JSONObject p=request.getJSONObject("parameters"); long duration=Math.round(p.getDouble("durationSeconds")*1_000_000);
            JSONArray refs=request.getJSONObject("input").getJSONArray("artifacts");boolean image=false;
            for(int i=0;i<refs.length();i++){JSONObject r=refs.getJSONObject(i);String role=r.getString("role");if(role.equals("visual"))image=app.artifacts.get(r.getString("artifactId")).getJSONObject("metadata").getString("mime").startsWith("image/");else mixer.add(input.file(role),p.getDouble(role.equals("voice")?"voiceGain":"musicGain"));}
            File visual=input.file("visual"),still=null,audio=null,output=app.artifacts.staging(id,"mp4");
            try {
                if(image){still=app.artifacts.staging(id,"mp4");File frames=app.artifacts.staging(id,"frames");try{stillFrames(visual,frames,duration,check);VideoEncoder.encode(frames,still,check,false);}finally{frames.delete();}visual=still;}
                audio=app.artifacts.staging(id,"mp4"); encodeAudio(mixer,audio,duration,check);
                mux(visual,audio,output,duration,check);
                JSONObject metadata=new MediaInspector().inspect(output);
                if(!metadata.getString("mime").equals("video/mp4")||metadata.optLong("durationMs")<=5000)throw new IOException("合成文件的实际时长或容器验证失败");
                MediaExtractor verify=new MediaExtractor();try{verify.setDataSource(output.getPath());boolean sound=false;for(int i=0;i<verify.getTrackCount();i++)sound|=verify.getTrackFormat(i).getString(MediaFormat.KEY_MIME).startsWith("audio/");if(!sound)throw new IOException("合成文件缺少实际音轨");}finally{verify.release();}
                return output;
            } finally {if(still!=null)still.delete();if(audio!=null)audio.delete();}
        }
    }
    private static void stillFrames(File image,File output,long duration,DataFiles.Check check) throws Exception {
        BitmapFactory.Options bounds=new BitmapFactory.Options();bounds.inJustDecodeBounds=true;BitmapFactory.decodeFile(image.getPath(),bounds);
        if(bounds.outWidth<1||bounds.outHeight<1||bounds.outWidth*(long)bounds.outHeight>4096L*4096)throw new IOException("图片无法解码或超过合成预算");
        BitmapFactory.Options options=new BitmapFactory.Options();options.inSampleSize=Math.max(1,Math.max(bounds.outWidth,bounds.outHeight)/640);
        Bitmap original=BitmapFactory.decodeFile(image.getPath(),options);if(original==null)throw new IOException("图片解码失败");Bitmap scaled=null;
        try {
            double ratio=Math.min(1,640.0/Math.max(original.getWidth(),original.getHeight()));int w=Math.max(64,((int)(original.getWidth()*ratio)/2)*2),h=Math.max(64,((int)(original.getHeight()*ratio)/2)*2);
            scaled=Bitmap.createScaledBitmap(original,w,h,true);int[] pixels=new int[w*h];scaled.getPixels(pixels,0,w,0,0,w,h);byte[] rgb=new byte[w*h*3];for(int i=0;i<pixels.length;i++){rgb[i*3]=(byte)(pixels[i]>>16);rgb[i*3+1]=(byte)(pixels[i]>>8);rgb[i*3+2]=(byte)pixels[i];}
            int count=(int)((duration*8+999999)/1000000);try(DataOutputStream out=new DataOutputStream(new BufferedOutputStream(new FileOutputStream(output)))){out.write(new byte[]{'L','M','A','F','R','M','1',0});for(int v:new int[]{w,h,count,8,3})out.writeInt(Integer.reverseBytes(v));for(int i=0;i<count;i++){check.run();out.write(rgb);}}
        }finally{if(scaled!=null&&scaled!=original)scaled.recycle();original.recycle();}
    }
    private static void encodeAudio(PcmMixer mixer,File output,long duration,DataFiles.Check check) throws Exception {
        MediaCodec codec=null;MediaMuxer muxer=null;boolean started=false;
        try {
            codec=MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_AUDIO_AAC);MediaFormat f=MediaFormat.createAudioFormat(MediaFormat.MIMETYPE_AUDIO_AAC,PcmMixer.RATE,1);f.setInteger(MediaFormat.KEY_AAC_PROFILE,MediaCodecInfo.CodecProfileLevel.AACObjectLC);f.setInteger(MediaFormat.KEY_BIT_RATE,128000);f.setInteger(MediaFormat.KEY_MAX_INPUT_SIZE,8192);codec.configure(f,null,null,MediaCodec.CONFIGURE_FLAG_ENCODE);codec.start();
            muxer=new MediaMuxer(output.getPath(),MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4);MediaCodec.BufferInfo info=new MediaCodec.BufferInfo();long total=duration*PcmMixer.RATE/1_000_000,submitted=0;boolean inputDone=false,done=false;int track=-1;long activity=System.nanoTime();
            while(!done){check.run();if(!inputDone){int index=codec.dequeueInputBuffer(10000);if(index>=0){ByteBuffer buffer=codec.getInputBuffer(index);buffer.clear();int count=(int)Math.min(buffer.remaining()/2,total-submitted);if(count>0)mixer.fill(buffer,submitted,count);codec.queueInputBuffer(index,0,count*2,submitted*1_000_000/PcmMixer.RATE,count==0?MediaCodec.BUFFER_FLAG_END_OF_STREAM:0);submitted+=count;inputDone=count==0;activity=System.nanoTime();}}
                int index=codec.dequeueOutputBuffer(info,10000);if(index==MediaCodec.INFO_OUTPUT_FORMAT_CHANGED){track=muxer.addTrack(codec.getOutputFormat());muxer.start();started=true;activity=System.nanoTime();}else if(index>=0){ByteBuffer bytes=codec.getOutputBuffer(index);if(info.size>0&&(info.flags&MediaCodec.BUFFER_FLAG_CODEC_CONFIG)==0){if(!started||bytes==null)throw new IOException("AAC 输出尚未就绪");bytes.position(info.offset);bytes.limit(info.offset+info.size);muxer.writeSampleData(track,bytes,info);}done=(info.flags&MediaCodec.BUFFER_FLAG_END_OF_STREAM)!=0;codec.releaseOutputBuffer(index,false);activity=System.nanoTime();}
                // Codec stall guard only; never a generation wall-clock limit.
                if(System.nanoTime()-activity>30_000_000_000L)throw new IOException("本机 AAC 编码器没有进展");
            }check.run();muxer.stop();started=false;
        }finally{if(codec!=null){try{codec.stop();}catch(Exception ignored){}codec.release();}if(muxer!=null){if(started)try{muxer.stop();}catch(Exception ignored){}muxer.release();}}
    }
    private static void mux(File video,File audio,File output,long duration,DataFiles.Check check)throws Exception{
        MediaExtractor v=new MediaExtractor(),a=new MediaExtractor();MediaMuxer muxer=null;boolean started=false;
        try{v.setDataSource(video.getPath());a.setDataSource(audio.getPath());int vi=track(v,"video/"),ai=track(a,"audio/");if(vi<0||ai<0)throw new IOException("缺少画面或音频轨道");MediaFormat vf=v.getTrackFormat(vi),af=a.getTrackFormat(ai);v.selectTrack(vi);a.selectTrack(ai);muxer=new MediaMuxer(output.getPath(),MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4);int vo=muxer.addTrack(vf),ao=muxer.addTrack(af);muxer.start();started=true;
            ByteBuffer buffer=ByteBuffer.allocateDirect(8*1024*1024);MediaCodec.BufferInfo info=new MediaCodec.BufferInfo();long originV=v.getSampleTime(),originA=a.getSampleTime();boolean vd=false,ad=false;
            while(!vd||!ad){check.run();long vt=vd?Long.MAX_VALUE:v.getSampleTime()-originV,at=ad?Long.MAX_VALUE:a.getSampleTime()-originA;boolean visual=vt<=at;MediaExtractor selected=visual?v:a;long time=visual?vt:at;buffer.clear();int size=selected.readSampleData(buffer,0);if(size<0||time>=duration){if(visual)vd=true;else ad=true;continue;}if(size>buffer.capacity())throw new IOException("单帧超过合成缓冲预算");if((selected.getSampleFlags()&MediaExtractor.SAMPLE_FLAG_ENCRYPTED)!=0)throw new IOException("不支持加密媒体轨道");info.set(0,size,Math.max(0,time),(selected.getSampleFlags()&MediaExtractor.SAMPLE_FLAG_SYNC)!=0?MediaCodec.BUFFER_FLAG_KEY_FRAME:0);muxer.writeSampleData(visual?vo:ao,buffer,info);if(!selected.advance()){if(visual)vd=true;else ad=true;}}
            check.run();muxer.stop();started=false;
        }finally{v.release();a.release();if(muxer!=null){if(started)try{muxer.stop();}catch(Exception ignored){}muxer.release();}}
    }
    private static int track(MediaExtractor e,String prefix){for(int i=0;i<e.getTrackCount();i++)if(e.getTrackFormat(i).getString(MediaFormat.KEY_MIME).startsWith(prefix))return i;return -1;}
}
