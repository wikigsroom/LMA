package com.lma.app;
import org.json.*;
import java.nio.file.*;

/** Host protocol fixture. Its arbitrary output bytes are never speech, a WAV, or model inference. */
public final class MossFixture {
    public static void main(String[] args) throws Exception {
        JSONObject request = new JSONObject(new String(Files.readAllBytes(Paths.get(args[0])), "UTF-8"));
        JSONObject components = request.getJSONObject("components");
        for (java.util.Iterator<String> it = components.keys(); it.hasNext();) if (!Files.isRegularFile(Paths.get(components.getString(it.next())))) throw new IllegalStateException("Missing fixture workspace link");
        System.out.println("{\"event\":\"stage\",\"stage\":\"host_protocol_fixture\"}"); System.out.flush();
        String prompt = request.getJSONObject("input").getString("prompt");
        if (prompt.equals("fixture wait")) { Thread.sleep(30000); return; }
        if (prompt.equals("fixture fail")) { System.out.println("{\"event\":\"error\",\"message\":\"Explicit host fixture failure\"}"); System.out.flush(); return; }
        Files.write(Paths.get(request.getString("output")), new byte[]{9,8,7});
        System.out.println(new JSONObject().put("event","execution").put("details",new JSONObject().put("effectiveParameters",request.getJSONObject("parameters")).put("hostFixture",true)));
        System.out.println(new JSONObject().put("event","complete").put("output",request.getString("output"))); System.out.flush();
    }
}
