# Original delayed-state failure / 原始排空状态失败

The first native run matches **0/5** official cases. The saved report, request,
stdout, stderr, driver, probe and original `delay.cpp` retain their original bytes.
This is a fixed-logit algorithm comparison, without backbone, codec, speech or
Android execution. It is not a speech-quality verdict.

原始问题：排空计数晚一步；截断少提取一帧；没有生成助手语音时误取用户参考片段。
dev.43 修正后的共用实现另做当前检查，不能改写这里的失败。

Official methods: [MOSS-TTS-v1.5 at the pinned revision](https://huggingface.co/OpenMOSS-Team/MOSS-TTS-v1.5/tree/cdd3b911b1585e3f2dbc7775ef10f9926f58850a).
Original native source: [openmoss delay.cpp](https://github.com/pwilkin/openmoss/blob/bfb1f465e0a86fb5a52bbf93e67ceba4b7d0b4e1/src/delay.cpp),
SPDX Apache-2.0; [license](https://github.com/pwilkin/openmoss/blob/bfb1f465e0a86fb5a52bbf93e67ceba4b7d0b4e1/LICENSE).
Original source attribution and license markers remain in the saved source.
