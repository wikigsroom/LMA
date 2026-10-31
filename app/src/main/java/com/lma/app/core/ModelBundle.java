package com.lma.app.core;

import org.json.JSONArray;
import org.json.JSONObject;
import java.net.URL;
import java.net.URI;
import java.util.*;

/** Pinned data-only recipe. An engine ID must resolve to code shipped in the APK. */
public final class ModelBundle {
    public static final String SCHEMA = "lma.model-bundle/1", SCHEMA_V2 = "lma.model-bundle/2";
    public final String id, modelId, recipeId, engine, architecture, pipeline, backend, name;
    public final List<Component> components;
    public final Set<String> tasks;
    private final JSONObject source;
    public static final class Component {
        public final String role, path, importPath, sha256, gitBlobSha1, objectId, integrityAlgorithm, url, format, repository, revision;
        public final long bytes;
        public final Set<String> provides;
        Component(JSONObject value, boolean version2) throws Exception {
            role = key(value.getString("role")); path = value.getString("path");
            Set<String> embedded = new LinkedHashSet<>();
            if (value.has("provides")) {
                JSONArray roles = value.getJSONArray("provides");
                if (roles.length() > 32) throw new IllegalArgumentException("Too many embedded component roles");
                for (int i = 0; i < roles.length(); i++) if (!embedded.add(key(roles.getString(i))) || roles.getString(i).equals(role)) throw new IllegalArgumentException("Duplicate embedded component role");
            }
            provides = Collections.unmodifiableSet(embedded);
            // HF paths are metadata, never filesystem destinations (objects use their SHA256).
            if (path.isEmpty() || path.length() > 2048 || path.indexOf('\\') >= 0 || path.chars().anyMatch(c -> c < 32 || c == 127)) throw new IllegalArgumentException("Invalid component path");
            for (String part : path.split("/", -1)) if (part.isEmpty() || part.equals(".") || part.equals("..")) throw new IllegalArgumentException("Invalid component path");
            importPath = value.optString("importPath", path);
            if (value.has("importPath") && !version2 || importPath.isEmpty() || importPath.length() > 2048 || importPath.indexOf('\\') >= 0 || importPath.chars().anyMatch(c -> c < 32 || c == 127)) throw new IllegalArgumentException("Invalid component import path");
            for (String part : importPath.split("/", -1)) if (part.isEmpty() || part.equals(".") || part.equals("..")) throw new IllegalArgumentException("Invalid component import path");
            sha256 = value.optString("sha256").toLowerCase(Locale.ROOT);
            gitBlobSha1 = value.optString("gitBlobSha1").toLowerCase(Locale.ROOT);
            if (!sha256.isEmpty() && !Protocol.isSha256(sha256) || !gitBlobSha1.isEmpty() && !gitBlobSha1.matches("[a-f0-9]{40}")) throw new IllegalArgumentException("Invalid component digest");
            if (version2 ? sha256.isEmpty() == gitBlobSha1.isEmpty() : sha256.isEmpty() || value.has("gitBlobSha1")) throw new IllegalArgumentException("Declare exactly one supported component digest; Git blobs require bundle v2");
            integrityAlgorithm = gitBlobSha1.isEmpty() ? "sha256" : "git_blob_sha1";
            objectId = gitBlobSha1.isEmpty() ? sha256 : ComponentIntegrity.gitObjectKey(gitBlobSha1);
            bytes = value.getLong("bytes");
            if (bytes < 1 || bytes > 128L * 1024 * 1024 * 1024) throw new IllegalArgumentException("Invalid component size");
            format = key(value.getString("format"));
            String lower = path.toLowerCase(Locale.ROOT);
            if (lower.matches(".*\\.(so|dll|exe|dex|jar|apk|py|sh|bat|cmd|ps1|js|html)$")) throw new IllegalArgumentException("Model bundles cannot supply executable code");
            url = value.optString("url"); repository = value.optString("repository"); revision = value.optString("revision");
            if (!gitBlobSha1.isEmpty() && (!url.startsWith("https://huggingface.co/") && !url.startsWith("https://hf-mirror.com/"))) throw new IllegalArgumentException("Git blob integrity requires a pinned HF source URL");
            if (!url.isEmpty()) {
                if (url.length() > 8192 || url.chars().anyMatch(c -> c < 32 || c == 127)) throw new IllegalArgumentException("Invalid component URL");
                URL parsed = new URL(url);
                if (!parsed.getProtocol().equals("https") || parsed.getHost().isEmpty() || parsed.getUserInfo() != null || parsed.getRef() != null) throw new IllegalArgumentException("Component download requires HTTPS");
                if (parsed.getHost().equalsIgnoreCase("huggingface.co") || parsed.getHost().equalsIgnoreCase("hf-mirror.com")) {
                    if (!repository.matches("[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+") || !revision.matches("[a-fA-F0-9]{40,64}")) throw new IllegalArgumentException("HF assets require a fixed repository revision");
                    if (parsed.getQuery() != null || !new URI(url).getPath().equals("/" + repository + "/resolve/" + revision + "/" + path)) throw new IllegalArgumentException("HF URL does not match the pinned asset");
                }
            }
        }
    }
    public ModelBundle(JSONObject value) throws Exception {
        String schema = value.getString("schema");
        if (!schema.equals(SCHEMA) && !schema.equals(SCHEMA_V2)) throw new IllegalArgumentException("Unsupported model bundle schema");
        id = key(value.getString("id")); modelId = key(value.getString("modelId")); recipeId = key(value.getString("recipeId"));
        engine = key(value.getString("engine")); architecture = key(value.getString("architecture"));
        pipeline = key(value.getString("pipeline")); backend = key(value.getString("backend"));
        name = value.getString("name").trim();
        if (name.isEmpty() || name.length() > 160) throw new IllegalArgumentException("Invalid model name");
        Set<String> checkedTasks = new LinkedHashSet<>(); JSONArray tags = value.getJSONArray("tasks");
        for (int i = 0; i < tags.length(); i++) {
            String tag = tags.getString(i);
            if (!Arrays.asList("text", "image", "video", "audio", "3d").contains(tag)) throw new IllegalArgumentException("Unknown output task");
            checkedTasks.add(tag);
        }
        if (checkedTasks.isEmpty()) throw new IllegalArgumentException("Missing output task");
        tasks = Collections.unmodifiableSet(checkedTasks);
        JSONArray files = value.getJSONArray("components");
        if (files.length() < 1 || files.length() > 512) throw new IllegalArgumentException("Invalid component count");
        List<Component> checked = new ArrayList<>(); Set<String> paths = new HashSet<>(), roles = new HashSet<>(); Map<String, Long> sizes = new HashMap<>();
        for (int i = 0; i < files.length(); i++) {
            Component c = new Component(files.getJSONObject(i), schema.equals(SCHEMA_V2));
            if (!paths.add(c.importPath.toLowerCase(Locale.ROOT)) || !roles.add(c.role)) throw new IllegalArgumentException("Component roles and paths must be unique");
            if (sizes.containsKey(c.objectId) && sizes.get(c.objectId) != c.bytes) throw new IllegalArgumentException("Conflicting size for shared component");
            sizes.put(c.objectId, c.bytes); checked.add(c);
        }
        components = Collections.unmodifiableList(checked);
        source = DataFiles.copy(value);
        ContentMetadata.validate(source.optJSONObject("content"));
        // Validate the schema before a recipe can be installed, even if settings are never opened.
        new ParameterSchema(source.optJSONObject("parameters") == null ? new JSONObject() : source.getJSONObject("parameters"));
        AdapterSpec.validate(this);
    }
    public JSONObject json() { return DataFiles.copy(source); }
    public ParameterSchema parameters() { return new ParameterSchema(source.optJSONObject("parameters") == null ? new JSONObject() : source.optJSONObject("parameters")); }
    public Component component(String role) {
        for (Component c : components) if (c.role.equals(role)) return c;
        throw new IllegalArgumentException("Missing component role: " + role);
    }
    public JSONObject tags() throws Exception {
        JSONArray task = new JSONArray(), dependency = new JSONArray(), formats = new JSONArray(); Set<String> unique = new LinkedHashSet<>();
        for (String t : tasks) task.put("task:" + t);
        Set<String> dependencies = new LinkedHashSet<>();
        for (Component c : components) { dependencies.add(c.role); dependencies.addAll(c.provides); unique.add(c.format); }
        for (String role : dependencies) dependency.put("dependency:" + role);
        for (String format : unique) formats.put("format:" + format);
        JSONArray capability = source.optJSONArray("capabilities") == null ? new JSONArray() : new JSONArray(source.getJSONArray("capabilities").toString());
        if (AdapterSpec.isAdapter(this)) {
            dependency.put("dependency:base_model"); boolean found = false;
            for (int i = 0; i < capability.length(); i++) if (capability.getString(i).equals("image_adapter")) found = true;
            if (!found) capability.put("image_adapter");
        }
        return new JSONObject().put("task", task).put("engine", "engine:" + engine).put("pipeline", "pipeline:" + pipeline).put("backend", "backend:" + backend)
                .put("dependency", dependency).put("format", formats).put("capability", capability).put("architecture", "architecture:" + architecture).put("kind", AdapterSpec.isAdapter(this) ? "kind:adapter" : "kind:model")
                .put("content", source.has("content") ? new JSONArray().put("content:" + source.getJSONObject("content").getString("classification")).put("content_basis:" + source.getJSONObject("content").getString("basis")) : new JSONArray());
    }
    public static String key(String value) { return Protocol.safeId(value); }
}
