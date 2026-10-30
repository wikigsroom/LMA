package com.lma.app;

import android.net.Uri;
import com.lma.app.core.BundleTransfers;
import java.io.InputStream;
import java.util.concurrent.ConcurrentHashMap;

/** Host document-provider port only. The production Android bridge is compiled separately. */
public final class DocumentInput implements BundleTransfers.Input {
    static final ConcurrentHashMap<String, BundleTransfers.Input> providers = new ConcurrentHashMap<>();
    private final BundleTransfers.Input source;
    public DocumentInput(LmaApp.Resolver resolver, Uri uri) {
        BundleTransfers.Input selected = providers.get(uri.toString());
        source = selected == null ? () -> resolver.openInputStream(uri) : selected;
    }
    public InputStream open() throws Exception { return source.open(); }
    public void cancel() { source.cancel(); }
}
