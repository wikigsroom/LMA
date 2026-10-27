package com.lma.app;
import org.json.JSONObject;
import java.io.*;
import java.nio.file.*;
/** Protocol/process fixture. Writes arbitrary bytes, never generated audio or model output. */
public final class WorkerFixture {
    public static void main(String[] args) throws Exception {
        JSONObject request = new JSONObject(new String(Files.readAllBytes(Paths.get(args[0])), "UTF-8"));
        String mode = request.getString("fixture"), output = request.getString("output");
        if (mode.equals("wait")) { System.out.println("{\"event\":\"stage\",\"stage\":\"fixture_wait\"}"); System.out.flush(); Thread.sleep(30000); return; }
        if (mode.equals("long")) { char[] data = new char[66000]; java.util.Arrays.fill(data, 'x'); System.out.println(data); return; }
        System.out.println("{\"event\":\"stage\",\"stage\":\"fixture_stage\"}");
        System.out.println("{\"event\":\"execution\",\"details\":{\"effectiveParameters\":{\"speaker\":0}}}");
        System.out.println("{\"event\":\"execution\",\"details\":{\"audio\":{\"fixture\":true}}}");
        System.out.println("{\"event\":\"progress\",\"stage\":\"fixture_progress\",\"fraction\":0.5}");
        Files.write(Paths.get(output), new byte[]{1,2,3});
        if (mode.equals("error")) System.out.println("{\"event\":\"error\",\"message\":\"Explicit fixture error\"}");
        if (!mode.equals("missing")) System.out.println(new JSONObject().put("event", "complete").put("output", mode.equals("wrong") ? output + "-wrong" : output));
        if (mode.equals("duplicate")) System.out.println(new JSONObject().put("event", "complete").put("output", output));
        System.out.flush();
        if (mode.equals("exit")) System.exit(2);
    }
}
