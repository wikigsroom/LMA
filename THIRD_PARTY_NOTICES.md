# Third-party code and model terms / 第三方代码与模型条款

The LMA-authored code is MIT-licensed. This does not relicense bundled libraries,
ported algorithms, optional model weights, LoRA files or tokenizers. Complete
notices are shipped in `third_party/notices/` and the App's license page; source
revisions, hashes and native dependencies are recorded in
`third_party/engine-lock.json` and the individual source locks.

LMA 自有代码采用 MIT；第三方代码和用户选择的模型资产保留各自条款。
APK 的许可证页面与源码保留完整声明，不以模型标签代替使用许可。

| Component / 组件 | Source / 来源 | Terms / 条款与修改 |
| --- | --- | --- |
| Dolphin 3 / Llama 3.2 tool-template configuration — Built with Llama | dphn/Dolphin3.0-Llama3.2-1B `e753b6ebd7adf87036eb6a3e6de68acca5850e2f` | Publisher declares `llama3.2`; attribution and complete Community License retained in `chat-template-dolphin3-llama32-NOTICE.txt`, shipped with the APK. LMA preserves ordinary GGUF chat and adapts structured tool rendering; no trained weights or tokenizer vocabulary bundled. 发布者标注 Llama 3.2 条款，保留完整许可及派生修改说明。 |
| DISO forward surface kernels | SarahWeiii/diso `9792ad928ccb09bdec938779651ee03e395758a6` | **CC BY-NC 4.0; noncommercial / 非商业**. CUDA launches and indexing converted to bounded CPU loops; gradients omitted. Included in `liblma-rf-shape.so`; see `expansion-shape-DISO-LICENSE.txt`. |
| Lewiner extraction | scikit-image `51b3367761a52ab9111bdbd9537272d7dd2eccde`; neurolabusc/LewinerMarchingCubes `23642e6716c77ac15a2c2349b5125d605ac76234` | Original BSD/MIT notices retained; file writers omitted, lookup tables retained. |
| FDG / volume material helpers | microsoft/TRELLIS.2 and FlexGEMM, pinned in `third_party/fdg-source-lock.json` | Original MIT notices; tensor bindings replaced by C++ vectors and bounded CPU indexing. Eigen MPL2 subset retained with accompanying notices. |
| DIS / ISNetDIS definitions | xuebinqin/DIS `b6764e20381f6f42a70f83fa3324181529ed1403` | Apache-2.0 source notice; exported user-selected weights remain separate. |
| Vision language runtime | llama.cpp `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4` | MIT and bundled hash / media component notices retained; static isolated CPU mtmd runtime. |
| MoGe / DA3 / timm definitions | Revisions in `third_party/depth-notice-lock.json` | Complete pinned publisher license texts retained; no depth weights bundled. |

The noncommercial DISO component means the complete APK must not be described
as an unrestricted all-MIT distribution. Consult the complete component license
for redistribution and use; omitting weights does not remove code obligations.

完整 APK 含有 DISO 非商业条款组件，不能称为“全部 MIT、无商业限制”的分发包。
其他运行库、网络定义和模型条款参见完整 notices、来源锁与用户所选模型的许可。
