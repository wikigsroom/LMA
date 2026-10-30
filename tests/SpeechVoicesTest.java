package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.file.Files;
import java.util.*;

/** Actual local headers and adversarial metadata, without loading or executing weights. */
public final class SpeechVoicesTest {
    private static int checks;
    private interface Attempt { void run() throws Exception; }
    private static void check(boolean v, String why) { if (!v) throw new AssertionError(why); checks++; }
    private static void rejects(Attempt run, String why) throws Exception {
        try { run.run(); } catch (Exception expected) { checks++; return; }
        throw new AssertionError(why);
    }
    private static JSONObject read(File f) throws Exception { return new JSONObject(new String(Files.readAllBytes(f.toPath()), "UTF-8")); }
    private static byte[] text(String s) throws Exception { return s.getBytes("UTF-8"); }
    private static byte[] concat(byte[]... parts) throws Exception { ByteArrayOutputStream o = new ByteArrayOutputStream(); for (byte[] p : parts) o.write(p); return o.toByteArray(); }
    private static byte[] varint(long n) { ByteArrayOutputStream o = new ByteArrayOutputStream(); do { int b = (int) (n & 127); n >>>= 7; o.write(n == 0 ? b : b | 128); } while (n != 0); return o.toByteArray(); }
    private static byte[] field(int number, byte[] value) throws Exception { return concat(varint((number << 3) | 2), varint(value.length), value); }
    private static byte[] meta(String key, String value) throws Exception { return field(14, concat(field(1, text(key)), field(2, text(value)))); }
    private static File write(File root, byte[] bytes) throws Exception { File f = new File(root, "header.onnx"); Files.write(f.toPath(), bytes); return f; }
    private static ParameterSchema schema() { return new ParameterSchema(new JSONObject().put("version", 1).put("fields", new JSONObject().put("speaker", new JSONObject().put("type", "integer").put("default", 0).put("minimum", 0).put("maximum", 127)))); }
    private static JSONObject speaker(ParameterSchema s) { return s.json().getJSONObject("fields").getJSONObject("speaker"); }
    private static ParameterSchema choices(JSONArray choices) { JSONObject j = schema().json(); j.getJSONObject("fields").getJSONObject("speaker").put("choices", choices); return new ParameterSchema(j); }
    private static JSONObject choice(Object value, String label) { return new JSONObject().put("value", value).put("label", label); }
    public static void main(String[] args) throws Exception {
        File root = new File(args[0]); root.mkdirs();
        byte[] count = meta("n_speakers", "2");
        File valid = write(root, concat(field(7, new byte[1024 * 1024]), count, meta("speaker_names", "First,Second"), meta("id2speaker", "1->Second,0->First")));
        Map<String, String> map = OnnxMetadata.read(valid);
        check(map.size() == 3 && map.get("n_speakers").equals("2"), "Metadata after a graph field is read without graph allocation");
        rejects(() -> map.put("x", "y"), "Metadata map is immutable");
        SpeechVoices voices = new SpeechVoices(); ParameterSchema original = schema(), effective = voices.onnx(original, valid);
        check(speaker(effective).getJSONArray("choices").getJSONObject(1).getString("label").equals("Second"), "Indexed mapping agrees with names");
        check(speaker(effective).getInt("maximum") == 1 && speaker(effective).getString("limitSource").equals("model_metadata"), "Actual local count bounds voice IDs");
        check(effective.normalize(new JSONObject().put("speaker", 999), new JSONObject()).getJSONObject("values").getInt("speaker") == 1, "Native schema clamps above the actual count");
        check(!speaker(original).has("choices") && speaker(original).getInt("maximum") == 127, "Effective schema cannot mutate the immutable recipe");
        JSONObject copy = effective.json(); speaker(new ParameterSchema(copy)).put("maximum", 99);
        check(speaker(effective).getInt("maximum") == 1, "Schema snapshots cannot mutate cached metadata");
        File changed = write(root, meta("n_speakers", "1"));
        check(speaker(voices.onnx(original, changed)).getInt("maximum") == 0, "File size change invalidates metadata cache");
        check(!speaker(voices.onnx(original, changed)).has("choices"), "A model with no names remains editable by ID");
        File missing = write(root, meta("other", "ignored"));
        check(!speaker(new SpeechVoices().onnx(original, missing)).has("actualVoiceCount"), "Missing count keeps an honest declared bound");
        for (String bad : new String[]{"0", "129", "-1", "NaN", "1.5", "99999999999"}) {
            File f = write(root, meta("n_speakers", bad)); rejects(() -> new SpeechVoices().onnx(original, f), "Invalid voice count rejected: " + bad);
        }
        for (String mapping : new String[]{"0->A,0->A", "0->A", "2->B,0->A", "x->B,0->A", "0A,1->B"}) {
            File f = write(root, concat(count, meta("id2speaker", mapping))); rejects(() -> new SpeechVoices().onnx(original, f), "Invalid mapping rejected: " + mapping);
        }
        File conflict = write(root, concat(count, meta("speaker_names", "A,B"), meta("id2speaker", "0->B,1->A")));
        rejects(() -> new SpeechVoices().onnx(original, conflict), "Conflicting name tables must not silently remap a voice");
        File shortNames = write(root, concat(count, meta("speaker_names", "A")));
        rejects(() -> new SpeechVoices().onnx(original, shortNames), "Name list count mismatch is rejected");
        File badLabel = write(root, concat(count, meta("speaker_names", "A,\nB")));
        check(speaker(new SpeechVoices().onnx(original, badLabel)).getJSONArray("choices").length() == 1, "Control-containing labels are omitted without changing numeric bounds");
        for (byte[] bytes : new byte[][]{
            {}, {(byte)128}, {0}, {11}, {114,5,10}, {114,2,10,5},
            concat(varint(7 << 3 | 1), new byte[3]), concat(varint(7 << 3 | 5), new byte[2]),
            concat(count, count), field(14, concat(field(1,text("n_speakers")),field(1,text("n_speakers")),field(2,text("1")))),
            field(14,concat(field(1,text("n_speakers")),field(2,new byte[]{(byte)0xc3,(byte)0x28}))),
            field(14,concat(field(1,text("speaker_names")),field(2,new byte[65537]))),
            {(byte)128,(byte)128,(byte)128,(byte)128,(byte)128,(byte)128,(byte)128,(byte)128,(byte)128,(byte)1}
        }) { File f = write(root, bytes); rejects(() -> OnnxMetadata.read(f), "Malformed protobuf must fail within bounded work"); }
        File reversed = write(root, field(14,concat(field(2,text("1")),field(1,text("n_speakers")))));
        check(OnnxMetadata.read(reversed).get("n_speakers").equals("1"), "Protobuf metadata ordering is not assumed");
        File unknown = write(root, concat(field(14,concat(field(1,text("ignored")),field(2,new byte[100000]))),count));
        check(OnnxMetadata.read(unknown).size() == 1, "Large irrelevant metadata values are skipped");
        ByteArrayOutputStream many = new ByteArrayOutputStream(); for (int i=0;i<513;i++) many.write(meta("other", "a"));
        File manyEntries = write(root,many.toByteArray()); rejects(() -> OnnxMetadata.read(manyEntries), "Metadata entry budget is enforced");
        JSONArray validChoices = new JSONArray().put(choice(0,"First")).put(choice(2,"Second")); ParameterSchema pick = choices(validChoices);
        check(pick.normalize(new JSONObject().put("speaker",1), new JSONObject()).getJSONObject("values").getInt("speaker") == 1, "Named choices are suggestions, not an enum restricting numeric editing");
        for (JSONArray bad : new JSONArray[]{new JSONArray().put(choice(0,"")),new JSONArray().put(choice(0," bad")),new JSONArray().put(choice(0,"a\nb")),new JSONArray().put(choice(128,"large")),new JSONArray().put(choice(-1,"small")),new JSONArray().put(choice(1.5,"fraction")),new JSONArray().put(choice("1","string")),new JSONArray().put(choice(1,"a")).put(choice(1,"b")),new JSONArray().put(choice(0,"extra").put("code",new JSONArray()))}) rejects(() -> choices(bad), "Invalid named numeric choice rejected");
        JSONObject limited = schema().json(); limited.getJSONObject("fields").getJSONObject("speaker").put("maximum",0);
        File two = write(root, concat(count,meta("speaker_names","A,B")));
        check(speaker(new SpeechVoices().onnx(new ParameterSchema(limited),two)).getInt("maximum") == 0, "Actual count cannot widen a recipe restriction");
        JSONObject fixture = read(new File(args[1])), paths = read(new File(args[2])); JSONArray observed = new JSONArray();
        for (Object raw : fixture.getJSONArray("models")) {
            JSONObject model = (JSONObject) raw; File file = new File(paths.getString(model.getString("id")));
            ParameterSchema actual = model.getString("kind").equals("nano") ? new SpeechVoices().nano(original,file) : new SpeechVoices().onnx(original,file);
            JSONObject f = speaker(actual); JSONArray names = model.getJSONArray("names");
            check(f.getInt("actualVoiceCount") == model.getInt("count"), model.getString("id") + " actual downloaded count");
            check(f.getInt("maximum") == model.getInt("count")-1, model.getString("id") + " actual bound");
            check(f.optJSONArray("choices") == null ? names.length()==0 : f.getJSONArray("choices").length()==names.length(), model.getString("id") + " actual name count");
            if(names.length()>0) {
                JSONArray choices=f.getJSONArray("choices"); for(int i=0;i<names.length();i++) if(choices.getJSONObject(i).getInt("value")!=i || !choices.getJSONObject(i).getString("label").equals(names.getString(i))) throw new AssertionError("Actual voice index/name mismatch");
                checks++;
            }
            observed.put(new JSONObject().put("id",model.getString("id")).put("voices",f.getInt("actualVoiceCount")).put("names",names.length()).put("source_sha256",model.getString("sha256")));
        }
        File nano = new File(root,"nano.json"); Files.write(nano.toPath(),text("{\"builtin_voices\":[{\"display_name\":\"Test\",\"prompt_audio_codes\":[1,2]}]}"));
        JSONObject nanoSchema=new SpeechVoices().nano(original,nano).json();
        check(!nanoSchema.toString().contains("prompt_audio_codes") && !nanoSchema.toString().contains("[1,2]"), "Only presentation names/count escape the Nano metadata reader");
        JSONObject catalog = read(new File(args[3])), old = read(new File(args[4]));
        BundleStore store = new BundleStore(new File(root,"store")); store.declare(new ModelBundle(old)); store.saveSettings(old.getString("id"),new JSONObject().put("speaker",5));
        JSONObject fresh=null; for(Object row:catalog.getJSONArray("bundles")) {JSONObject b=(JSONObject)row;store.declare(new ModelBundle(b));if(b.getString("id").equals("moss_nano_100m_onnx_catalogue_v1"))fresh=b;}
        check(fresh!=null && fresh.getJSONArray("components").toString().equals(old.getJSONArray("components").toString()), "New catalogue profile preserves all eleven exact original asset identities");
        check(store.snapshot().length()==catalog.getJSONArray("bundles").length()+1, "Imported immutable Nano profile coexists with new catalogue identity");
        BundleStore restored = new BundleStore(new File(root,"store"));
        check(restored.settings(old.getString("id")).getJSONObject("values").getInt("speaker")==5, "Catalogue upgrade preserves old imported voice settings");
        check(restored.settings(fresh.getString("id")).getJSONObject("values").getInt("speaker")==0, "Fresh catalogue identity has independent settings");
        System.out.println(new JSONObject().put("passed",true).put("checks",checks).put("actual_local_headers",observed).put("model_inference",false).put("android_device",false));
    }
}
