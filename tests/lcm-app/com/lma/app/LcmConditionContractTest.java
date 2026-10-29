package com.lma.app;
import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.file.*;
/** The supplied data stays in private test storage; this is parser evidence, not inference. */
public final class LcmConditionContractTest {
    public static void main(String[] args)throws Exception{
        JSONObject manifest=SdTrainedAppTest.read(new File(args[0]));File data=new File(args[1]);
        JSONArray components=manifest.getJSONArray("components");
        for(int i=0;i<components.length();i++)if(components.getJSONObject(i).getString("role").equals("condition_bias"))components.getJSONObject(i).put("bytes",data.length()).put("sha256",SdTrainedAppTest.sha(data));
        try{LcmCondition.verify(new ModelBundle(manifest),data);System.out.println("ACCEPT");}
        catch(Exception expected){System.out.println("REJECT");}
    }
}
