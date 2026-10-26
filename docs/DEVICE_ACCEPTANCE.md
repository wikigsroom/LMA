# 真实 Android 验收

当前没有 Android 真机。这里的工具已编译，未在设备上执行。只接受已授权 ADB 的 ARM64 Android 9+ 真机；拒绝 Android 模拟器，不调用 ROOT、Docker 或 WSL。

## 构建工具

在项目目录运行：

```powershell
python tools/build.py
python tools/build_acceptance.py
python tools/device_check.py
```

第一个 APK 为正常应用。build/device-tests/LMA-acceptance.apk 是独立验收工具，使用同一份本地签名，用户日常使用不需要安装它。签名私钥不会包含在交付源码 ZIP 内；从源码重新构建时，应保留原项目的 signing/ 才能覆盖升级现有安装。

未发现已授权真机时，预检记录 awaiting_physical_device 并以 2 退出，不会启动模拟器。

## 基础 Android 检查

手机连接并授权 USB 调试后，先解锁屏幕，停止当前对话，再运行：

```powershell
python tools/device_check.py --install --run
```

它保留应用数据并覆盖安装当前 APK，安装验收 APK，在 Android 上实际执行离线 WebView / JavaScript 桥接、目录加载、原生可执行文件权限、SQLite 中断恢复和前台服务设置命令。Android 13+ 的测试会通过已授权 ADB 授予本应用通知权限。

SQLite 测试创建并清理自己的临时会话，恢复此前所选会话。instrumentation 会重启目标应用，因此不要在正在下载或生成重要内容时运行。

## 完整模型与锁屏请求

```powershell
python tools/device_check.py --install --run --model m01 --minutes 15
```

此命令会在手机实际下载约 398 MB 的 Dolphin Qwen 0.5B（已有文件则复用并重新计算 SHA256），加载 APK 自带 ARM 原生引擎，通过应用真实 ChatRunner 生成并持久化回复。测试对话会留在应用中，已下载模型保留。

instrumentation 结束后，工具重新正常打开 LMA，等待模型和 API 恢复，通过临时 ADB 端口转发测试接口与错误密钥拒绝；随后退到桌面、关闭屏幕，从主机持续发出真实流式请求。此阶段没有附着 instrumentation，避免测试进程的优先级影响后台存活结论。每轮请求都要求真实输出、正常结束，并检查屏幕仍处于关闭状态。

该阶段验证的是屏幕关闭时的 FGS / API 运行。USB 供电和 ADB 已连接会影响系统电源策略，不能等同脱线、电池供电和厂商极限省电环境。它也不验证密码锁的交互。可使用已授权无线 ADB 进一步比较；工具不自行开启无线调试。

--model m06 可选择 LFM 1.2B，--model m08 可选择 Qwen 1.7B。--minutes 60 为一小时，最大允许 1440；最后一条请求可能使实际时长超出目标。--minutes 0 跳过屏幕关闭持续请求，不会把耐久验证标记为通过。多设备时使用 --serial 已授权设备序列号。

API 密钥只经受信任的测试进程传到主机内存，不输出到控制台，不写入验收报告。临时端口转发会在结束时移除。测试结束后模型服务继续按用户设置提供接口；可从 LMA 通知或界面停止。

## 结果与待补充场景

结果写入 build/device-tests/device-results.json。基础测试、真实推理和后台时长分别记录；不会用编译通过代替实测通过。

仍需手动或另行扩展验证实际 WLAN 的另一台客户端、SAF 文件提供器、通知停止与唤醒锁、下载网络切换、重启恢复及各模型的完整兼容性。长时间运行应记录供电、散热、系统电池策略、模型 SHA256、线程、上下文、温度与失败率。
