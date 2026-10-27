package com.lma.app;

import android.content.ContentResolver;
import android.database.Cursor;
import android.net.Uri;
import android.provider.DocumentsContract;
import com.lma.app.core.ModelBundle;
import org.json.JSONObject;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

/** Resolve a user-selected SAF folder; imported bundles never download missing files. */
public final class BundleDocuments {
    private BundleDocuments() {}
    public static JSONObject components(ContentResolver resolver, Uri tree, ModelBundle bundle) throws Exception {
        String root = DocumentsContract.getTreeDocumentId(tree); Map<String, String> directories = new HashMap<>(); directories.put("", root);
        JSONObject uris = new JSONObject();
        for (ModelBundle.Component component : bundle.components) {
            String current = root, prefix = ""; String[] parts = component.path.split("/");
            if (parts.length > 64) throw new IOException("组件路径过深");
            for (int i = 0; i < parts.length; i++) {
                String next = prefix.isEmpty() ? parts[i] : prefix + "/" + parts[i];
                if (directories.containsKey(next)) { current = directories.get(next); prefix = next; continue; }
                String found = null, mime = null;
                Uri children = DocumentsContract.buildChildDocumentsUriUsingTree(tree, current);
                try (Cursor cursor = resolver.query(children, new String[]{DocumentsContract.Document.COLUMN_DOCUMENT_ID, DocumentsContract.Document.COLUMN_DISPLAY_NAME, DocumentsContract.Document.COLUMN_MIME_TYPE}, null, null, null)) {
                    if (cursor != null) while (cursor.moveToNext()) if (parts[i].equals(cursor.getString(1))) {
                        if (found != null) throw new IOException("文件夹内存在重名组件：" + next);
                        found = cursor.getString(0); mime = cursor.getString(2);
                    }
                }
                if (found == null) throw new IOException("所选文件夹缺少组件：" + component.path + "；不会改为网络下载");
                if (i < parts.length - 1 && !DocumentsContract.Document.MIME_TYPE_DIR.equals(mime) || i == parts.length - 1 && DocumentsContract.Document.MIME_TYPE_DIR.equals(mime)) throw new IOException("组件路径类型不匹配：" + component.path);
                current = found; prefix = next;
                if (i < parts.length - 1) directories.put(prefix, current);
            }
            uris.put(component.role, DocumentsContract.buildDocumentUriUsingTree(tree, current).toString());
        }
        return uris;
    }
}
