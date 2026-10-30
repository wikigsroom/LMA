package android.content;

import android.content.res.AssetFileDescriptor;
import android.net.Uri;
import android.os.CancellationSignal;

/** Host document-provider boundary only; never included in the APK. */
public abstract class ContentResolver {
    public abstract AssetFileDescriptor openAssetFileDescriptor(Uri uri, String mode, CancellationSignal signal) throws Exception;
}
