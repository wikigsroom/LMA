# LMA local capability gateway

[中文操作说明](../../docs/LOCAL_API_V0312.md) · [English guide](../../docs/LOCAL_API_V0312.en.md)

Opt-in native Go extension for `Wei-Shaw/sub2api` v0.2.19, commit `dece26153621959ccd7635814f4b2d08304e681a`. It retains Sub2API's auth/group allowlists and routes by the Android phone's published capabilities. It performs no inference, creates no cloud fallback and does not rewrite production DB account/model mappings.

```text
python tools/apply_sub2api.py --source PATH_TO_EXACT_ISOLATED_SUB2API_SOURCE
python tools/test_sub2api_gateway.py --upstream-source PATH_TO_PATCHED_SOURCE
```

`localgateway/` is a standard-library-only Go module. `lma_local.go.txt` is the Gin adapter installed by the apply tool; `lma_local_test.go.txt` exercises it with an explicitly declared auth-context fixture. Runtime configuration is opt-in with `SUB2API_LMA_CONFIG`; see the bilingual guide for group IDs, credential environment variables, private durable state, sync and ownership rules.

`localgateway/cmd/probe` is strictly a development forwarding harness with explicit fixed Alice/Bob credentials. **Do not deploy it as an authenticated production gateway.** The phone key exists only in its environment during the authorized test. Production uses the Gin adapter and original Sub2API authentication.

Tests distinguish fixtures, actual upstream source compilation and real phone calls. Neither a fixture nor a successful model response proves live production billing or model quality. Use native build tools; no Docker, WSL or emulator is required.

Text prefill/loading uses its own HTTP transport without a response-header execution deadline; ordinary control/media requests retain independent network guards. A real HTTP regression fixture verifies delayed text headers outlive a deliberately shortened ordinary header budget. 文本加载／首段生成的响应头等待不设置固定执行截止，普通网络保护保持独立；不是通过延长所有网络超时来伪装不限时。
