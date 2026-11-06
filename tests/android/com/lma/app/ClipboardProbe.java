package com.lma.app;
import android.app.Instrumentation;
import android.app.Activity;
import android.content.ClipboardManager;
import android.content.ClipData;
import android.content.Context;
import android.os.Bundle;
/** Writes only the explicitly supplied acceptance prompt; never reads user clipboard. */
public final class ClipboardProbe extends Instrumentation {
    private String text;
    @Override public void onCreate(Bundle args) { super.onCreate(args); text=args.getString("text", ""); start(); }
    @Override public void onStart() {
        Bundle result=new Bundle();
        try {
            if(text.isEmpty()||text.length()>12000) throw new IllegalArgumentException("Invalid owned prompt");
            ClipboardManager clipboard=(ClipboardManager)getTargetContext().getSystemService(Context.CLIPBOARD_SERVICE);
            clipboard.setPrimaryClip(ClipData.newPlainText("LMA acceptance prompt",text));result.putString("status","copied_owned_prompt");finish(Activity.RESULT_OK,result);
        } catch(Exception error) {result.putString("status","failed");finish(Activity.RESULT_CANCELED,result);}
    }
}
