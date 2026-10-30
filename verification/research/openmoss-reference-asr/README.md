# Original reference recognition / 原始参考识别

The first original transcription remains in `original-transcriptions.json`.
`dev42-final-transcriptions.json` preserves the exact publicly committed report
from `9ab05996a60f5537e41815b29d780df978f242a0` without reconstructing it.
Both concern original dev.41/42 WAVs, with two controls passing and reference mode
failing text following. They do not validate corrected dev.43 output.

首次及最终 dev.42 报告分别保留原字节；原参考失败不覆盖，不以新模型输出替代旧 WAV。
Fresh corrected-model recognition, when executed, is a separate report.
No ASR data enter the APK and no off-device inference is used.
