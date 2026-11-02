package com.lma.app.core;
import org.json.JSONObject;
import java.io.*;
import java.util.*;

/** Bounded PCM WAV readers, linear resampling, mono mix, clipping and explicit silence padding. */
public final class PcmMixer implements AutoCloseable {
    public static final int RATE=44100;
    private final List<Source> sources=new ArrayList<>();
    public void add(File file,double gain) throws Exception { if(!Double.isFinite(gain)||gain<0||gain>2) throw new IllegalArgumentException("音量无效"); sources.add(new Source(file,gain)); }
    public short sample(long frame) throws IOException { double sum=0; for(Source s:sources)sum+=s.at(frame*(double)s.rate/RATE)*s.gain; return (short)Math.round(Math.max(-1,Math.min(1,sum))*32767); }
    public void fill(java.nio.ByteBuffer output,long first,int count) throws IOException {output.order(java.nio.ByteOrder.LITTLE_ENDIAN);for(int i=0;i<count;i++) output.putShort(sample(first+i));}
    @Override public void close() {for(Source s:sources) try{s.file.close();}catch(IOException ignored){}sources.clear();}
    private static final class Source {
        final RandomAccessFile file; final int rate,channels,bits,format,align; final long offset,frames; final double gain;
        byte[] cache; long cacheStart=-1; int cached;
        Source(File path,double gain) throws Exception {
            JSONObject m=WaveFile.inspect(path); if(m.getInt("channels")>2||m.getLong("durationMs")>60000) throw new IOException("合成 WAV 仅接受不超过 60 秒的单声道或双声道");
            this.gain=gain; rate=m.getInt("sampleRate"); channels=m.getInt("channels");bits=m.getInt("bitsPerSample");format=m.getInt("formatCode");align=channels*bits/8;
            file=new RandomAccessFile(path,"r"); long found=0,size=0;
            try {file.seek(12);while(file.getFilePointer()<file.length()){int tag=file.readInt();long bytes=Integer.toUnsignedLong(Integer.reverseBytes(file.readInt())),start=file.getFilePointer();if(tag==0x64617461){if(found!=0)throw new IOException("多数据块 WAV 请先转换为普通 PCM WAV");found=start;size=bytes;}file.seek(start+bytes+(bytes&1));}if(found==0)throw new IOException("WAV 没有采样数据");}
            catch(Exception e){file.close();throw e;}offset=found;frames=size/align;cache=new byte[4096*align];
        }
        double at(double frame) throws IOException {long low=(long)frame;if(low>=frames)return 0;double a=read(low),b=low+1<frames?read(low+1):a;return a+(b-a)*(frame-low);}
        double read(long frame) throws IOException {
            if(frame<cacheStart||frame>=cacheStart+cached){cacheStart=frame;cached=(int)Math.min(4096,frames-frame);file.seek(offset+frame*align);file.readFully(cache,0,cached*align);}
            int start=(int)(frame-cacheStart)*align;double sum=0;
            for(int c=0;c<channels;c++){int at=start+c*bits/8;if(format==3){int value=(cache[at]&255)|(cache[at+1]&255)<<8|(cache[at+2]&255)<<16|cache[at+3]<<24;float f=Float.intBitsToFloat(value);if(!Float.isFinite(f))throw new IOException("WAV 中有无效采样");sum+=f;}
                else if(bits==16)sum+=(short)((cache[at]&255)|cache[at+1]<<8)/32768.0;
                else if(bits==24)sum+=((cache[at]&255)|(cache[at+1]&255)<<8|cache[at+2]<<16)/8388608.0;
                else sum+=((cache[at]&255)|(cache[at+1]&255)<<8|(cache[at+2]&255)<<16|cache[at+3]<<24)/2147483648.0;}
            return sum/channels;
        }
    }
}
