package com.lma.app;

import android.graphics.BitmapFactory;
import android.media.MediaExtractor;
import android.media.MediaFormat;
import org.json.JSONObject;
import java.io.*;
import com.lma.app.core.ArtifactStore;

/** Inspect imported/generated local media, never trusting a supplied extension or description. */
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
    private JSONObject wave(File file) throws Exception { return com.lma.app.core.WaveFile.inspect(file); }
    private JSONObject video(File file) throws Exception {
        MediaExtractor extractor = new MediaExtractor();
        try {
            extractor.setDataSource(file.getPath());
            for (int i = 0; i < extractor.getTrackCount(); i++) {
                MediaFormat f = extractor.getTrackFormat(i);
                if (f.getString(MediaFormat.KEY_MIME).startsWith("video/")) {
                    extractor.selectTrack(i); int frames = 0; long previous = -1, last = 0;
                    do { long time = extractor.getSampleTime(); if (time < 0) break; if (Thread.currentThread().isInterrupted()) throw new IOException("Media inspection was stopped"); if (frames >= 1000000) throw new IOException("Video frame table exceeds the import/output limit"); if (time < previous) throw new IOException("视频时间戳顺序无效"); previous = time; last = time; frames++; } while (extractor.advance());
                    if (f.getInteger(MediaFormat.KEY_WIDTH) < 1 || f.getInteger(MediaFormat.KEY_HEIGHT) < 1 || f.getInteger(MediaFormat.KEY_WIDTH) > 16384 || f.getInteger(MediaFormat.KEY_HEIGHT) > 16384) throw new IOException("Video dimensions exceed the local media limit");
                    if (frames < 2 || last <= 0) throw new IOException("视频缺少连续帧");
                    return new JSONObject().put("mime", "video/mp4").put("codec", f.getString(MediaFormat.KEY_MIME)).put("width", f.getInteger(MediaFormat.KEY_WIDTH)).put("height", f.getInteger(MediaFormat.KEY_HEIGHT))
                            .put("frames", frames).put("fps", f.containsKey(MediaFormat.KEY_FRAME_RATE) ? f.getInteger(MediaFormat.KEY_FRAME_RATE) : JSONObject.NULL).put("durationMs", f.containsKey(MediaFormat.KEY_DURATION) ? f.getLong(MediaFormat.KEY_DURATION) / 1000 : last / 1000);
                }
            }
            throw new IOException("MP4 没有可解码的视频轨道");
        } finally { extractor.release(); }
    }
}
