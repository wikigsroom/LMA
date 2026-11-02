package com.lma.app.core;
import org.json.JSONObject;
import java.util.Locale;
/** Add structured advice only to newly observed failures; historical errors remain unchanged. */
public final class TaskFailures {
    private TaskFailures(){}
    public static JSONObject describe(String message)throws Exception {
        String value=message==null?"":message.toLowerCase(Locale.ROOT),code="local_execution_error",action="查看原始阶段和错误，编辑参数后创建新尝试；保留本次记录";
        if(value.contains("empty_structure")){code="empty_structure";action="所选 3D 路线未产生有效几何；保留原失败，检查输入物体、分割和后端数值，或明确选择其他路线";}
        else if(value.contains("hash")||value.contains("sha256")||value.contains("哈希")){code="integrity_mismatch";action="核对固定文件版本与配对 SHA256；重新选择或显式重新导入，不覆盖其他共享资产";}
        else if(value.contains("memory")||value.contains("oom")||value.contains("内存")){code="out_of_memory";action="释放手机内存或降低尺寸、帧数、上下文；选择更小的已安装合法配方后新建任务";}
        else if(value.contains("unsupported")||value.contains("不支持")||value.contains("未适配")){code="unsupported_operation";action="选择接受此输入的模型 / 适配器；格式或模型名称本身不代表已接入";}
        else if(value.contains("corrupt")||value.contains("损坏")||value.contains("decode")||value.contains("解码")||value.contains("wav")||value.contains("mp4")){code="invalid_media";action="重新选择可正常打开的素材，并核对容器、音轨、采样格式与时长；保留原件";}
        else if(value.contains("空间")||value.contains("storage")){code="insufficient_storage";action="明确清理不再被任务 / 会话使用的文件，保留共享素材后重试";}
        return new JSONObject().put("code",code).put("nextAction",action).put("checkpointResumable",false);
    }
}
