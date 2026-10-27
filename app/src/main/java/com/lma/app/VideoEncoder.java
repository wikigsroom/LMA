package com.lma.app;

import android.media.Image;
import android.media.MediaCodec;
import android.media.MediaCodecInfo;
import android.media.MediaFormat;
import android.media.MediaMuxer;
import com.lma.app.core.DataFiles;
import java.io.*;
import java.nio.ByteBuffer;
import java.util.Arrays;

/** Stream generated RGB frames through the phone's AVC encoder; no external conversion. */
public final class VideoEncoder {
    private VideoEncoder() {}
    private static int integer(DataInputStream in) throws IOException { return Integer.reverseBytes(in.readInt()); }
    public static void encode(File frames, File output, DataFiles.Check check) throws Exception {
        MediaCodec codec = null; MediaMuxer muxer = null; boolean muxing = false;
        try (DataInputStream in = new DataInputStream(new BufferedInputStream(new FileInputStream(frames)))) {
            byte[] magic = new byte[8]; in.readFully(magic);
            if (!Arrays.equals(magic, new byte[]{'L','M','A','F','R','M','1',0})) throw new IOException("生成帧文件版本无效");
            int width = integer(in), height = integer(in), count = integer(in), fps = integer(in), channels = integer(in);
            if (width < 64 || height < 64 || width > 2048 || height > 2048 || width % 2 != 0 || height % 2 != 0 || count < 2 || count > 129 || fps < 1 || fps > 60 || channels != 3 || frames.length() != 28L + width * (long) height * 3 * count) throw new IOException("生成帧尺寸或总长度无效");
            codec = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC);
            MediaFormat format = MediaFormat.createVideoFormat(MediaFormat.MIMETYPE_VIDEO_AVC, width, height);
            format.setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Flexible);
            format.setInteger(MediaFormat.KEY_BIT_RATE, Math.max(256000, Math.min(12000000, width * height * fps / 5)));
            format.setInteger(MediaFormat.KEY_FRAME_RATE, fps); format.setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1);
            codec.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE); codec.start();
            muxer = new MediaMuxer(output.getPath(), MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4);
            MediaCodec.BufferInfo info = new MediaCodec.BufferInfo(); int submitted = 0, track = -1; boolean inputDone = false, outputDone = false, moving = false;
            byte[] rgb = new byte[width * height * 3], first = null; long activity = System.nanoTime();
            while (!outputDone) {
                check.run();
                if (!inputDone) {
                    int input = codec.dequeueInputBuffer(10000);
                    if (input >= 0) {
                        if (submitted == count) { codec.queueInputBuffer(input, 0, 0, submitted * 1_000_000L / fps, MediaCodec.BUFFER_FLAG_END_OF_STREAM); inputDone = true; }
                        else {
                            in.readFully(rgb); if (first == null) first = rgb.clone(); else if (!Arrays.equals(first, rgb)) moving = true;
                            Image image = codec.getInputImage(input); if (image == null) throw new IOException("本机 AVC 编码器没有可写入的 YUV 图像接口");
                            try { yuv(image, rgb, width, height); } finally { image.close(); }
                            codec.queueInputBuffer(input, 0, width * height * 3 / 2, submitted * 1_000_000L / fps, 0); submitted++;
                        }
                        activity = System.nanoTime();
                    }
                }
                int encoded = codec.dequeueOutputBuffer(info, 10000);
                if (encoded == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                    if (muxing) throw new IOException("视频编码格式重复变化"); track = muxer.addTrack(codec.getOutputFormat()); muxer.start(); muxing = true; activity = System.nanoTime();
                } else if (encoded >= 0) {
                    ByteBuffer bytes = codec.getOutputBuffer(encoded);
                    if ((info.flags & MediaCodec.BUFFER_FLAG_CODEC_CONFIG) == 0 && info.size > 0) {
                        if (!muxing || bytes == null) throw new IOException("视频编码输出尚未准备好"); bytes.position(info.offset); bytes.limit(info.offset + info.size); muxer.writeSampleData(track, bytes, info);
                    }
                    outputDone = (info.flags & MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0; codec.releaseOutputBuffer(encoded, false); activity = System.nanoTime();
                }
                if (System.nanoTime() - activity > 30_000_000_000L) throw new IOException("本机视频编码器长时间没有进展");
            }
            if (!moving) throw new IOException("生成结果只有重复静态帧，未作为运动视频完成任务");
            check.run(); muxer.stop(); muxing = false;
        } finally {
            if (codec != null) { try { codec.stop(); } catch (Exception ignored) {} codec.release(); }
            if (muxer != null) { if (muxing) try { muxer.stop(); } catch (Exception ignored) {} muxer.release(); }
        }
    }
    private static void yuv(Image image, byte[] rgb, int width, int height) throws IOException {
        Image.Plane[] planes = image.getPlanes(); if (planes.length != 3) throw new IOException("本机编码器不支持 YUV420 输入");
        ByteBuffer y = planes[0].getBuffer(), u = planes[1].getBuffer(), v = planes[2].getBuffer();
        for (int row = 0; row < height; row++) for (int col = 0; col < width; col++) {
            int at = (row * width + col) * 3, r = rgb[at] & 255, g = rgb[at + 1] & 255, b = rgb[at + 2] & 255;
            y.put(row * planes[0].getRowStride() + col * planes[0].getPixelStride(), (byte) (((66 * r + 129 * g + 25 * b + 128) >> 8) + 16));
            if ((row & 1) == 0 && (col & 1) == 0) {
                int rr = 0, gg = 0, bb = 0;
                for (int dy = 0; dy < 2; dy++) for (int dx = 0; dx < 2; dx++) { int p = ((row + dy) * width + col + dx) * 3; rr += rgb[p] & 255; gg += rgb[p + 1] & 255; bb += rgb[p + 2] & 255; }
                r = rr / 4; g = gg / 4; b = bb / 4;
                u.put(row / 2 * planes[1].getRowStride() + col / 2 * planes[1].getPixelStride(), (byte) (((-38 * r - 74 * g + 112 * b + 128) >> 8) + 128));
                v.put(row / 2 * planes[2].getRowStride() + col / 2 * planes[2].getPixelStride(), (byte) (((112 * r - 94 * g - 18 * b + 128) >> 8) + 128));
            }
        }
    }
}
