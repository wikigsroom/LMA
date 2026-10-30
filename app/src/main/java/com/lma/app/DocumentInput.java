package com.lma.app;

import android.content.ContentResolver;
import android.content.res.AssetFileDescriptor;
import android.net.Uri;
import android.os.CancellationSignal;
import com.lma.app.core.BundleTransfers;
import java.io.IOException;
import java.io.InputStream;

/** One explicitly selected document; its cancellation signal is valid before open begins. */
public final class DocumentInput implements BundleTransfers.Input {
    private final ContentResolver resolver;
    private final Uri uri;
    private final CancellationSignal cancellation = new CancellationSignal();
    public DocumentInput(ContentResolver resolver, Uri uri) { this.resolver = resolver; this.uri = uri; }
    @Override public InputStream open() throws Exception {
        cancellation.throwIfCanceled();
        AssetFileDescriptor descriptor = resolver.openAssetFileDescriptor(uri, "r", cancellation);
        if (descriptor == null) throw new IOException("Cannot open selected document");
        InputStream stream = null;
        try {
            cancellation.throwIfCanceled();
            stream = descriptor.createInputStream();
            cancellation.throwIfCanceled();
            return stream;
        } catch (Exception error) {
            try { if (stream == null) descriptor.close(); else stream.close(); }
            catch (IOException closeError) { error.addSuppressed(closeError); }
            throw error;
        }
    }
    @Override public void cancel() { cancellation.cancel(); }
}
