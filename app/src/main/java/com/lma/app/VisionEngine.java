package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.util.*;

/** Owned CPU foreground/VLM workers; no server, remote executor or model acquisition. */
public final class VisionEngine implements LocalEngine {
    private final LmaApp app;private final File binary;private final JSONObject build;private final NativeWorker.Launcher launcher;
    public VisionEngine(LmaApp app,File binary,JSONObject build){this(app,binary,build,ProcessBuilder::start);}
    VisionEngine(LmaApp app,File binary,JSONObject build,NativeWorker.Launcher launcher){this.app=app;this.binary=binary;this.build=DataFiles.copy(build);this.launcher=launcher;}
    @Override public String id(){return "vision_cpu";}
    @Override public JSONObject describe()throws Exception{return DataFiles.copy(build).put("available",binary.isFile()&&binary.canExecute()).put("deviceValidated",false);}
    @Override public void validate(ModelBundle b,String type)throws Exception {if(!binary.isFile()||!binary.canExecute())throw new IOException("尚未安装匹配的视觉基座");VisionSpec.validate(b,type);}
    @Override public ParameterSchema schema(ModelBundle b)throws Exception {
        int bound=0;if(!VisionSpec.foreground(b.pipeline)&&app.bundles!=null&&app.bundles.hasObject(b.component("model")))bound=GgufMetadata.read(app.bundles.object(b.component("model").objectId)).optInt("contextLength");
        JSONObject schema=VisionSpec.schema(b.pipeline,bound),fields=schema.getJSONObject("fields"),selected=b.parameters().normalize(new JSONObject(),new JSONObject()).getJSONObject("values");
        for(Iterator<String> it=fields.keys();it.hasNext();){String key=it.next();if(selected.has(key))fields.getJSONObject(key).put("default",selected.get(key));}
        JSONObject defaults=new ParameterSchema(schema).normalize(new JSONObject(),new JSONObject()).getJSONObject("values");for(Iterator<String> it=fields.keys();it.hasNext();){String key=it.next();fields.getJSONObject(key).put("default",defaults.get(key));}return new ParameterSchema(schema);
    }
    @Override public InputSpec inputs(ModelBundle b,String type)throws Exception{return VisionSpec.inputs();}
    @Override public JSONObject prepare(ModelBundle b,JSONObject request)throws Exception {JSONObject copy=DataFiles.copy(request),p=schema(b).normalize(new JSONObject(),request.getJSONObject("parameters"));return copy.put("parameters",p.getJSONObject("values")).put("adjustments",p.getJSONArray("adjustments"));}
    @Override public File generate(Context context)throws Exception {
        BundleStore.Lease lease=context.model();boolean fg=VisionSpec.foreground(lease.bundle.pipeline);validate(lease.bundle,context.request().getString("type"));if(!context.adapters().isEmpty())throw new IOException("视觉准备不接受 LoRA");context.check();
        JSONObject parameters=schema(lease.bundle).normalize(new JSONObject(),context.request().getJSONObject("parameters"));if(parameters.getJSONArray("adjustments").length()!=0)throw new IOException("视觉参数变化，请重新提交任务");
        EngineWorkspace workspace=new EngineWorkspace(new File(app.getFilesDir(),"engine-work"),context::check);final Process[] child={null};
        try{JSONObject assets=new JSONObject();Map<String,String> layout=VisionSpec.layout(lease.bundle.pipeline);for(ModelBundle.Component c:lease.bundle.components)assets.put(c.role,workspace.linkRelative("models/"+layout.get(c.role),lease.file(c.role)).getPath());
            File image=context.input("reference_image");RfShapeSpec.reference(image);File out=context.output(fg?"png":"json");
            JSONObject command=new JSONObject().put("schema","lma.engine-request/1").put("pipeline",lease.bundle.pipeline).put("type",fg?"image.generate":"text.generate").put("parameters",parameters.getJSONObject("values")).put("workspace",new File(workspace.directory(),"models").getPath()).put("components",assets).put("referenceImage",workspace.link("inputs","reference.png",image).getPath()).put("output",out.getPath());
            NativeWorker.run(app,binary,context,command,out,Collections.emptyMap(),builder->{child[0]=launcher.start(builder);return child[0];});if(!fg)VisionSpec.partCount(out);context.check();return out;
        }finally{workspace.closeAfter(child[0]);}
    }
}
