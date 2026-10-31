package com.lma.app.core;

import java.net.URI;
import java.util.Arrays;
import java.util.Locale;
import org.json.JSONArray;
import org.json.JSONObject;

/** Content declarations do not imply architecture support, safety, or measured output quality. */
public final class ContentMetadata {
    private ContentMetadata() {}
    public static void validate(JSONObject value) throws Exception {
        if (value == null) return;
        String classification = value.getString("classification"), basis = value.getString("basis");
        if (!Arrays.asList("nsfw", "sensitive", "unclassified").contains(classification)) throw new IllegalArgumentException("Unknown content classification");
        if (!Arrays.asList("none", "publisher_card", "publisher_filename", "publisher_rating", "mirror_card", "hf_sensitive_tag", "hf_nsfw_tag", "repository_hint").contains(basis)) throw new IllegalArgumentException("Unknown content evidence basis");
        if (classification.equals("unclassified") != basis.equals("none")) throw new IllegalArgumentException("Unclassified content must not claim a checked declaration");
        if (classification.equals("sensitive") != basis.equals("hf_sensitive_tag")) throw new IllegalArgumentException("HF sensitive metadata is distinct from NSFW declarations");
        if (value.optBoolean("modelQualityTested")) throw new IllegalArgumentException("Content labels cannot claim measured model quality");
        if (value.optString("summary").length() > 1000) throw new IllegalArgumentException("Content note too long");
        String url = value.optString("sourceUrl");
        if (!url.isEmpty()) {
            URI uri = new URI(url);
            if (!"https".equals(uri.getScheme()) || uri.getUserInfo() != null || uri.getPort() != -1 || !Arrays.asList("huggingface.co", "civitai.com").contains(uri.getHost())) throw new IllegalArgumentException("Content evidence requires an original public source URL");
        }
        if (value.has("sourceRevision") && !value.getString("sourceRevision").matches("[a-f0-9]{40,64}")) throw new IllegalArgumentException("Content evidence revision must be pinned");
    }
    public static JSONObject repository(String id, JSONArray tags) throws Exception {
        boolean nsfw = false, sensitive = false;
        for (int i = 0; tags != null && i < Math.min(tags.length(), 200); i++) {
            String tag = tags.optString(i).toLowerCase(Locale.ROOT);
            nsfw |= tag.equals("nsfw"); sensitive |= tag.equals("not-for-all-audiences");
        }
        boolean hint = id.toLowerCase(Locale.ROOT).contains("nsfw");
        String classification = nsfw || hint ? "nsfw" : sensitive ? "sensitive" : "unclassified";
        String basis = nsfw ? "hf_nsfw_tag" : hint ? "repository_hint" : sensitive ? "hf_sensitive_tag" : "none";
        return new JSONObject().put("classification", classification).put("basis", basis).put("modelQualityTested", false)
                .put("sourceUrl", "https://huggingface.co/" + id)
                .put("summary", nsfw || hint ? "HF 标签或仓库名称中的 NSFW 提示；未逐项核对作者声明、模型文件或输出效果。" : sensitive ? "HF 标记不适合所有受众；这不等于已确认 NSFW 生成能力。" : "来源没有明确内容声明；不据此推断模型只生成一般内容。" );
    }
}
