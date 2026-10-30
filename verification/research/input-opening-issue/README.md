# Pending local document open / 等待打开本地文件

The production dev.43 transfer pauses an active read, but its opener is not registered before `Input.open()`. The actual host fixture blocks in open, queues a second explicit import, pauses the first, and fails because the queue remains blocked. The test finally releases its own opener; no process is abandoned.

保留首次失败、原生产传输源码、原测试与驱动的完整字节。此记录只证明原生 Windows Java 中的取消与队列缺口，不代表 Android 文件提供者或实际模型通过。源模型和网络均未使用。修复结果另行记录，不覆盖原失败。
