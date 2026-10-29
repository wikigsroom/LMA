    // SPDX-License-Identifier: Apache-2.0
    // Preserve the publisher's three separate F32 operations.
    ggml_tensor* modulate(ggml_context* ctx,ggml_tensor* x,ggml_tensor* shift,
                          ggml_tensor* scale,ggml_tensor* one) {
        return ggml_add(ctx,ggml_mul(ctx,x,ggml_add(ctx,scale,one)),shift);
    }
