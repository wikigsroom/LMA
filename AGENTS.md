# LMA repository instructions / 仓库工作约定

- Work inside this repository and the user's designated `无审查小模型/` directory. Do not invoke Docker, WSL, virtual machines, or Android emulators. 使用原生工具，不调度任何虚拟化环境。
- Close all browser pages, contexts, and browser processes created for a task in `finally` blocks. 浏览器调用结束必须关闭不用的页面并释放内存。
- Built-in catalogue entries must be publisher-declared Uncensored / Abliterated variants. Preserve pinned author evidence, weight revisions, sizes, and SHA256 checks. Do not silently replace them with ordinary base models. 自定义导入不得冒充已核对条目。
- Keep private keys, passwords, API keys, model weights, build caches, and personal browser profiles out of Git, source archives, logs, screenshots, and releases. Preserve the existing local `signing/` files for APK upgrades.
- Describe desktop checks, interface fixtures, and actual Android acceptance separately. Never claim phone inference, tokens/s, refusal-rate measurements, or background endurance without corresponding device evidence.
- **For every subsequent authorized LMA update, synchronize the code, Chinese and English READMEs/guides, relevant screenshots/GIFs, `CHANGELOG.md`, and version-specific release notes before committing and pushing to `git@github.com:wikigsroom/LMA.git`.** This is the user's standing instruction. 后续更新必须同步更新代码、双语文档、相关演示与更新说明并推送；远端受阻则保留本地提交并明确说明。
- Publish a new APK release only with consistent version fields, current verification fingerprints, APK/source hashes, validation records, and the original signing identity. Never replace an existing release asset with different bytes under the same filename; use a new version.
- Existing Git history and remote branches must be preserved. Do not force-push or rewrite published tags.
- Follow [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/RELEASING.md](docs/RELEASING.md) for the concrete update workflow. Do not infer a request for background scheduling from the synchronization instruction.
