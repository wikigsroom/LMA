package com.lma.app;

import android.graphics.BitmapFactory;
import android.media.MediaExtractor;
import android.media.MediaFormat;
import org.json.JSONObject;
import java.io.*;
import com.lma.app.core.ArtifactStore;

/** Read output metadata from local media, never from model-supplied descriptions. */
public final class MediaInspector implements ArtifactStore.Inspector {
    @Override public JSONObject inspect(File file) throws Exception {
        byte[] header = new byte[16]; int read;
        try (InputStream in = new FileInputStream(file)) { read = in.read(header); }
        if (file.getName().endsWith(".json")) return com.lma.app.core.TextResult.inspect(file);
        if (read < 12) throw new IOException("生成文件不完整");
        if ((header[0] & 255) == 137 && header[1] == 'P' && header[2] == 'N' && header[3] == 'G' || (header[0] & 255) == 255 && (header[1] & 255) == 216) {
            BitmapFactory.Options options = new BitmapFactory.Options(); options.inJustDecodeBounds = true; BitmapFactory.decodeFile(file.getPath(), options);
            if (options.outWidth < 1 || options.outHeight < 1 || options.outWidth > 16384 || options.outHeight > 16384) throw new IOException("无法解码生成图片");
            BitmapFactory.Options thumbnail = new BitmapFactory.Options(); thumbnail.inSampleSize = 1;
            while (options.outWidth / thumbnail.inSampleSize > 512 || options.outHeight / thumbnail.inSampleSize > 512) thumbnail.inSampleSize *= 2;
            android.graphics.Bitmap decoded = BitmapFactory.decodeFile(file.getPath(), thumbnail);
            if (decoded == null) throw new IOException("生成图片无法解码像素数据"); decoded.recycle();
            return new JSONObject().put("mime", options.outMimeType).put("width", options.outWidth).put("height", options.outHeight);
        }
        if (header[0] == 'R' && header[1] == 'I' && header[2] == 'F' && header[3] == 'F' && header[8] == 'W' && header[9] == 'A' && header[10] == 'V' && header[11] == 'E') return wave(file);
        if (header[4] == 'f' && header[5] == 't' && header[6] == 'y' && header[7] == 'p') return video(file);
        throw new IOException("生成文件不是可识别的图片、WAV、MP4 或文本结果");
    }
    private JSONObject wave(File file) throws Exception {
        try (RandomAccessFile in = new RandomAccessFile(file, "r")) {
            in.seek(12); int channels = 0, rate = 0, bits = 0, format = 0; long dataBytes = 0;
            while (in.getFilePointer() <= in.length() - 8) {
                int tag = in.readInt(); long size = Integer.toUnsignedLong(Integer.reverseBytes(in.readInt())), next = in.getFilePointer() + size + (size & 1);
                if (next > in.length() + 1 || size > in.length()) throw new IOException("WAV 数据块不完整");
                if (tag == 0x666d7420) {
                    if (size < 16) throw new IOException("WAV 格式数据缺失");
                    format = Short.toUnsignedInt(Short.reverseBytes(in.readShort())); channels = Short.toUnsignedInt(Short.reverseBytes(in.readShort())); rate = Integer.reverseBytes(in.readInt());
                    in.skipBytes(6); bits = Short.toUnsignedInt(Short.reverseBytes(in.readShort()));
                } else if (tag == 0x64617461) dataBytes += size;
                in.seek(next);
            }
            if ((format != 1 && format != 3) || format == 3 && bits != 32 || channels < 1 || channels > 8 || rate < 8000 || rate > 192000 || (bits != 16 && bits != 24 && bits != 32) || dataBytes < channels * bits / 8 || dataBytes % (channels * bits / 8) != 0) throw new IOException("WAV 采样格式不受支持或音频为空");
            return new JSONObject().put("mime", "audio/wav").put("sampleRate", rate).put("channels", channels).put("bitsPerSample", bits).put("samples", dataBytes / (channels * bits / 8)).put("durationMs", dataBytes * 8000 / (channels * (long) bits * rate));
        }
    }
    private JSONObject video(File file) throws Exception {
        MediaExtractor extractor = new MediaExtractor();
        try {
            extractor.setDataSource(file.getPath());
            for (int i = 0; i < extractor.getTrackCount(); i++) {
                MediaFormat f = extractor.getTrackFormat(i);
                if (f.getString(MediaFormat.KEY_MIME).startsWith("video/")) {
                    extractor.selectTrack(i); int frames = 0; long previous = -1, last = 0;
                    do { long time = extractor.getSampleTime(); if (time < 0) break; if (time < previous) throw new IOException("视频时间戳顺序无效"); previous = time; last = time; frames++; } while (extractor.advance());
                    if (frames < 2 || last <= 0) throw new IOException("视频缺少连续帧");
                    return new JSONObject().put("mime", "video/mp4").put("codec", f.getString(MediaFormat.KEY_MIME)).put("width", f.getInteger(MediaFormat.KEY_WIDTH)).put("height", f.getInteger(MediaFormat.KEY_HEIGHT))
                            .put("frames", frames).put("fps", f.containsKey(MediaFormat.KEY_FRAME_RATE) ? f.getInteger(MediaFormat.KEY_FRAME_RATE) : JSONObject.NULL).put("durationMs", f.containsKey(MediaFormat.KEY_DURATION) ? f.getLong(MediaFormat.KEY_DURATION) / 1000 : last / 1000);
                }
            }
            throw new IOException("MP4 没有可解码的视频轨道");
        } finally { extractor.release(); }
    }
}
