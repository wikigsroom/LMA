# Interrupted scratch-only experiment / 主动停止的单项缓存实验

This uses the original dev.41/42 worker/DelayState and the original reference
request, changing only the batch-encoder scratch lifetime. At 2085.897 seconds,
step 365/375, the developer stopped this owned experiment to prioritize the
corrected production prompt/delay/codec implementation. No WAV or complete
execution result exists. **It is incomplete, not a timeout or a passing output.**

该记录不能证明语音字节相同、正常结束、资源适配、Android 或 Release 通过。
`developer-interruption.json` gives the explicit interruption reason;
`results.json` retains raw observed termination and does not call it a timeout.
Requests, raw logs, driver, original capture helper and both compiled candidate
source units are preserved. Old worker/static-library identities are recorded in
the original report; they were not rebuilt from the later modified source.

The native source units derive from
[openmoss at the pinned revision](https://github.com/pwilkin/openmoss/tree/bfb1f465e0a86fb5a52bbf93e67ceba4b7d0b4e1),
Apache-2.0; original attribution/SPDX markers remain. See its
[license](https://github.com/pwilkin/openmoss/blob/bfb1f465e0a86fb5a52bbf93e67ceba4b7d0b4e1/LICENSE).
