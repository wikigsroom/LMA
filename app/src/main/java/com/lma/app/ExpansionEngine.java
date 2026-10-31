package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.util.*;

/** Actual signed CPU adapters sharing the existing model store, queue and result lifecycle. */
public final class ExpansionEngine implements LocalEngine {
    private final LmaApp app;
    private final File binary;
    private final JSONObject build;
    private final NativeWorker.Launcher launcher;
    public ExpansionEngine(LmaApp app, File binary, JSONObject build) { this(app,binary,build,ProcessBuilder::start); }
    ExpansionEngine(LmaApp app, File binary, JSONObject build, NativeWorker.Launcher launcher) {
        this.app=app; this.binary=binary; this.build=DataFiles.copy(build); this.launcher=launcher;
    }
    @Override public String id() { return build.optString("engine"); }
    private boolean multiView() { return id().equals("pixal_multiview"); }
    private boolean mesh() { return id().equals("trellis_native") || multiView(); }
    private JSONObject meshParameters(ModelBundle b,JSONObject p)throws Exception { return multiView()?MultiViewSpec.parameters(p):MeshSpec.parameters(b.pipeline,p); }
    private void meshAssets(ModelBundle b,JSONObject p)throws Exception { if(multiView())MultiViewSpec.assets(b,p);else MeshSpec.assets(b,p); }
    @Override public JSONObject describe() throws Exception { return DataFiles.copy(build).put("available",binary.isFile() && binary.canExecute()).put("deviceValidated",false); }
    @Override public ParameterSchema schema(ModelBundle bundle) throws Exception {
        JSONObject definition=multiView()?MultiViewSpec.schema():mesh() ? MeshSpec.schema(bundle.pipeline) : AudioCppSpec.schema(bundle.pipeline);
        JSONObject fields=definition.getJSONObject("fields"), selected=bundle.parameters().normalize(new JSONObject(),new JSONObject()).getJSONObject("values"), defaults=new JSONObject();
        for(Iterator<String> it=fields.keys();it.hasNext();) { String key=it.next(); if(selected.has(key))defaults.put(key,selected.get(key)); }
        JSONObject values=new ParameterSchema(definition).normalize(new JSONObject(),defaults).getJSONObject("values");
        for(Iterator<String> it=fields.keys();it.hasNext();) { String key=it.next(); fields.getJSONObject(key).put("default",values.get(key)); }
        return new ParameterSchema(definition);
    }
    @Override public InputSpec inputs(ModelBundle bundle, String type) throws Exception {
        return multiView()?MultiViewSpec.inputs():mesh() ? MeshSpec.inputs() : AudioCppSpec.inputs(bundle.pipeline);
    }
    @Override public void validate(ModelBundle bundle, String type) throws Exception {
        if (!binary.isFile() || !binary.canExecute()) throw new IOException("当前 App 未安装匹配的原生引擎");
        if(multiView())MultiViewSpec.validate(bundle,type);else if (mesh()) MeshSpec.validate(bundle,type); else AudioCppSpec.validate(bundle,type);
    }
    @Override public JSONObject prepare(ModelBundle bundle, JSONObject request) throws Exception {
        if (!mesh()) TtsSpec.text(request.getJSONObject("input"));
        JSONObject normalized=mesh() ? meshParameters(bundle,request.getJSONObject("parameters")) :
            AudioCppSpec.parameters(bundle.pipeline,request.getJSONObject("parameters"));
        if (mesh()) meshAssets(bundle,normalized.getJSONObject("values"));
        JSONObject result=DataFiles.copy(request); JSONArray adjustments=result.optJSONArray("adjustments");
        if (adjustments==null) adjustments=new JSONArray();
        JSONArray added=normalized.getJSONArray("adjustments"); for(int i=0;i<added.length();i++) adjustments.put(added.get(i));
        return result.put("parameters",normalized.getJSONObject("values")).put("adjustments",adjustments);
    }
    @Override public File generate(Context context) throws Exception {
        JSONObject request=context.request(); BundleStore.Lease lease=context.model(); validate(lease.bundle,request.getString("type")); context.check();
        if(!context.adapters().isEmpty()) throw new IOException("此引擎不接受图像 LoRA");
        JSONObject normalized=mesh()?meshParameters(lease.bundle,request.getJSONObject("parameters")):
            AudioCppSpec.parameters(lease.bundle.pipeline,request.getJSONObject("parameters"));
        if(normalized.getJSONArray("adjustments").length()!=0) throw new IOException("参数已超出当前基座范围，请重新提交任务");
        if (mesh()) meshAssets(lease.bundle,normalized.getJSONObject("values"));
        Map<String,String> layout=multiView()?MultiViewSpec.layout():mesh()?MeshSpec.layout(lease.bundle.pipeline):
            AudioCppSpec.layout(lease.bundle.pipeline,lease.bundle.component("model").format.equals("gguf"));
        EngineWorkspace workspace=new EngineWorkspace(new File(app.getFilesDir(),"engine-work"),context::check); final Process[] child={null};
        try {
            JSONObject components=new JSONObject();
            for(ModelBundle.Component c:lease.bundle.components) {
                String name=layout.get(c.role);
                if(c.role.equals("vocoder") && c.format.equals("bin")) name="vocos.bin";
                components.put(c.role,workspace.linkRelative("models/"+name,lease.file(c.role)).getPath());
            }
            File output=context.output(mesh()?"glb":"wav");
            File nativeOutput=multiView()?new File(workspace.directory(),"result.glb"):output;
            JSONObject command=new JSONObject().put("schema","lma.engine-request/1").put("type",request.getString("type"))
                .put("pipeline",lease.bundle.pipeline).put("input",request.getJSONObject("input")).put("parameters",normalized.getJSONObject("values"))
                .put("components",components).put("workspace",new File(workspace.directory(),"models").getPath()).put("output",nativeOutput.getPath());
            if(multiView()) {
                for(int i=0;i<4;i++){
                    File view=context.input(MultiViewSpec.ROLES[i]);MultiViewSpec.reference(view);
                    workspace.link("views",MultiViewSpec.FILES[i],view);
                }
                command.put("viewsDirectory",new File(workspace.directory(),"views").getPath());
            } else if(mesh()) command.put("referenceImage",workspace.link("inputs","reference.png",context.input("reference_image")).getPath());
            else {
                TtsSpec.text(request.getJSONObject("input")); JSONArray refs=request.getJSONObject("input").optJSONArray("artifacts");
                if(refs!=null && refs.length()>0) {
                    if(refs.length()!=1 || !refs.getJSONObject(0).getString("role").equals("reference_audio")) throw new IOException("只接受一个明确选择的参考音频");
                    File audio=context.input("reference_audio"); AudioCppSpec.reference(audio,lease.bundle.pipeline);
                    command.put("referenceAudio",workspace.link("inputs","reference.wav",audio).getPath());
                }
            }
            NativeWorker.run(app,binary,context,command,nativeOutput,Collections.emptyMap(),builder->{ child[0]=launcher.start(builder); return child[0]; });
            if(mesh()) GlbFile.inspect(nativeOutput); else WaveFile.inspect(nativeOutput);
            if(multiView()){context.check();DataFiles.move(nativeOutput,output);}
            return output;
        } finally { workspace.closeAfter(child[0]); }
    }
}
