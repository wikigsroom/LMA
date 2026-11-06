package com.lma.app.core;

import org.json.JSONArray;
import org.json.JSONObject;
import java.math.BigDecimal;
import java.net.URI;
import java.time.*;
import java.util.*;
import java.util.regex.Pattern;

/** Bounded local JSON Schema validation. References never access a URL or a file. */
public final class JsonSchema {
    private static final Set<String> KEYS = new HashSet<>(Arrays.asList("$schema", "$id", "$ref", "$defs", "definitions", "title", "description", "default", "examples", "type", "properties", "required", "additionalProperties", "anyOf", "oneOf", "allOf", "not", "enum", "const", "items", "prefixItems", "minItems", "maxItems", "uniqueItems", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf", "minLength", "maxLength", "pattern", "format", "minProperties", "maxProperties"));
    private JsonSchema() {}
    private static void budget(int[] left, int depth, String at) { if (--left[0] < 0 || depth > 64) throw new RequestError(at, "JSON Schema validation exceeds its bounded complexity"); }
    private static void fail(String at, String message) { throw new RequestError(at, message); }
    public static void check(JSONObject root, String at) throws Exception { check(root, root, at, 0, new int[]{20000}); }
    private static void check(JSONObject root, Object raw, String at, int depth, int[] left) throws Exception {
        budget(left, depth, at); if (raw instanceof Boolean) return;
        if (!(raw instanceof JSONObject)) { fail(at, "Expected a JSON Schema object or boolean"); return; }
        JSONObject schema = (JSONObject)raw;
        for (Iterator<String> it = schema.keys(); it.hasNext();) { String key = it.next(); if (!KEYS.contains(key)) fail(at + "." + key, "Unsupported JSON Schema keyword"); }
        if (schema.has("$ref")) { Object ref = schema.get("$ref"); if (!(ref instanceof String)) fail(at + ".$ref", "Use a local JSON pointer"); resolve(root, (String)ref, at); }
        if (schema.has("type")) {
            Object type = schema.get("type"); JSONArray types = type instanceof JSONArray ? (JSONArray)type : new JSONArray().put(type);
            if (types.length() == 0 || types.length() > 7) fail(at + ".type", "Invalid schema type");
            for (int i = 0; i < types.length(); i++) if (!(types.get(i) instanceof String) || !Arrays.asList("object", "array", "string", "number", "integer", "boolean", "null").contains(types.getString(i))) fail(at + ".type", "Invalid schema type");
        }
        for (String key : Arrays.asList("properties", "$defs", "definitions")) if (schema.has(key)) {
            if (!(schema.get(key) instanceof JSONObject)) fail(at + "." + key, "Expected a schema map");
            JSONObject map = schema.getJSONObject(key);
            for (Iterator<String> it = map.keys(); it.hasNext();) { String name = it.next(); check(root, map.get(name), at + "." + key + "." + name, depth + 1, left); }
        }
        for (String key : Arrays.asList("additionalProperties", "not")) if (schema.has(key)) check(root, schema.get(key), at + "." + key, depth + 1, left);
        if (schema.has("items")) check(root, schema.get("items"), at + ".items", depth + 1, left);
        for (String key : Arrays.asList("anyOf", "oneOf", "allOf", "prefixItems")) if (schema.has(key)) {
            if (!(schema.get(key) instanceof JSONArray)) fail(at + "." + key, "Expected a schema array");
            JSONArray values = schema.getJSONArray(key); if (values.length() == 0 || values.length() > 1024) fail(at + "." + key, "Invalid schema array length");
            for (int i = 0; i < values.length(); i++) check(root, values.get(i), at + "." + key + "[" + i + "]", depth + 1, left);
        }
        if (schema.has("required")) { JSONArray values = schema.getJSONArray("required"); Set<String> seen = new HashSet<>(); for (int i = 0; i < values.length(); i++) if (!(values.get(i) instanceof String) || !seen.add(values.getString(i))) fail(at + ".required", "Required property names must be unique strings"); }
        if (schema.has("enum") && (!(schema.get("enum") instanceof JSONArray) || schema.getJSONArray("enum").length() == 0)) fail(at + ".enum", "Use a nonempty enum array");
        for (String key : Arrays.asList("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf", "minLength", "maxLength", "minItems", "maxItems", "minProperties", "maxProperties")) if (schema.has(key)) {
            Object n = schema.get(key); if (!(n instanceof Number) || !Double.isFinite(((Number)n).doubleValue())) fail(at + "." + key, "Use a finite numeric bound");
            if (key.equals("multipleOf") && ((Number)n).doubleValue() <= 0) fail(at + "." + key, "multipleOf must be positive");
            if (Arrays.asList("minLength", "maxLength", "minItems", "maxItems", "minProperties", "maxProperties").contains(key) && (((Number)n).doubleValue() < 0 || ((Number)n).doubleValue() != Math.floor(((Number)n).doubleValue()))) fail(at + "." + key, "Use a nonnegative integer bound");
        }
        if (schema.has("uniqueItems") && !(schema.get("uniqueItems") instanceof Boolean)) fail(at + ".uniqueItems", "Use a boolean");
        if (schema.has("pattern")) safePattern(schema.getString("pattern"), at + ".pattern");
        if (schema.has("format") && !Arrays.asList("date-time", "date", "time", "email", "hostname", "ipv4", "ipv6", "uuid", "uri", "uri-reference").contains(schema.getString("format"))) fail(at + ".format", "Unsupported schema format");
    }
    private static Pattern safePattern(String value, String at) {
        if (value.length() > 256 || value.contains("(?") || value.matches(".*\\\\[1-9].*") || Pattern.compile("\\([^)]*[+*{|][^)]*\\)[+*{]").matcher(value).find()) { fail(at, "Use a bounded pattern without backreferences, lookarounds or nested repetition"); }
        try { return Pattern.compile(value); } catch (RuntimeException error) { fail(at, "Invalid schema pattern"); return null; }
    }
    private static Object resolve(JSONObject root, String ref, String at) throws Exception {
        if (ref.equals("#")) return root;
        if (!ref.startsWith("#/")) { fail(at + ".$ref", "Only document-local JSON references are supported"); return null; }
        Object value = root;
        for (String part : ref.substring(2).split("/", -1)) {
            String name = part.replace("~1", "/").replace("~0", "~");
            if (!(value instanceof JSONObject) || !((JSONObject)value).has(name)) { fail(at + ".$ref", "Unresolved local schema reference"); return null; }
            value = ((JSONObject)value).get(name);
        }
        return value;
    }
    public static void validate(JSONObject root, Object value) throws Exception { validate(root, root, value, "arguments", 0, new int[]{40000}); }
    private static void validate(JSONObject root, Object raw, Object value, String at, int depth, int[] left) throws Exception {
        budget(left, depth, at);
        if (raw instanceof Boolean) { if (!(Boolean)raw) fail(at, "Value is forbidden by the schema"); return; }
        JSONObject schema = (JSONObject)raw;
        if (schema.has("$ref")) validate(root, resolve(root, schema.getString("$ref"), at), value, at, depth + 1, left);
        if (schema.has("type")) {
            Object rawTypes = schema.get("type"); JSONArray types = rawTypes instanceof JSONArray ? (JSONArray)rawTypes : new JSONArray().put(rawTypes); boolean ok = false;
            for (int i = 0; i < types.length(); i++) ok |= isType(types.getString(i), value);
            if (!ok) fail(at, "Generated value has the wrong schema type");
        }
        String canonical = null;
        if (schema.has("const") && !canonical(schema.get("const")).equals(canonical(value))) fail(at, "Generated value differs from const");
        if (schema.has("enum")) { canonical = canonical(value); boolean found = false; JSONArray values = schema.getJSONArray("enum"); for (int i = 0; i < values.length(); i++) found |= canonical.equals(canonical(values.get(i))); if (!found) fail(at, "Generated value is outside the enum"); }
        for (String key : Arrays.asList("anyOf", "oneOf", "allOf")) if (schema.has(key)) {
            JSONArray branches = schema.getJSONArray(key); int matches = 0;
            for (int i = 0; i < branches.length(); i++) { try { validate(root, branches.get(i), value, at, depth + 1, left); matches++; } catch (RequestError error) { if (left[0] < 0) throw error; } }
            if (key.equals("anyOf") && matches == 0 || key.equals("oneOf") && matches != 1 || key.equals("allOf") && matches != branches.length()) fail(at, "Generated value does not satisfy " + key);
        }
        if (schema.has("not")) { boolean matches = true; try { validate(root, schema.get("not"), value, at, depth + 1, left); } catch (RequestError error) { if (left[0] < 0) throw error; matches = false; } if (matches) fail(at, "Generated value matches a forbidden schema"); }
        if (value instanceof JSONObject) {
            JSONObject object = (JSONObject)value, properties = schema.optJSONObject("properties");
            if (properties == null) properties = new JSONObject();
            JSONArray required = schema.optJSONArray("required"); if (required != null) for (int i = 0; i < required.length(); i++) if (!object.has(required.getString(i))) fail(at, "A required property is missing");
            for (Iterator<String> it = object.keys(); it.hasNext();) {
                String name = it.next(); if (properties.has(name)) validate(root, properties.get(name), object.get(name), at + "." + name, depth + 1, left);
                else if (schema.has("additionalProperties")) validate(root, schema.get("additionalProperties"), object.get(name), at + "." + name, depth + 1, left);
            }
            bound(schema, object.length(), "minProperties", "maxProperties", at);
        }
        if (value instanceof JSONArray) {
            JSONArray array = (JSONArray)value, prefix = schema.optJSONArray("prefixItems"); Set<String> unique = schema.optBoolean("uniqueItems") ? new HashSet<>() : null;
            for (int i = 0; i < array.length(); i++) {
                if (prefix != null && i < prefix.length()) validate(root, prefix.get(i), array.get(i), at + "[" + i + "]", depth + 1, left);
                else if (schema.has("items")) validate(root, schema.get("items"), array.get(i), at + "[" + i + "]", depth + 1, left);
                if (unique != null && !unique.add(canonical(array.get(i)))) fail(at, "Array items must be unique");
            }
            bound(schema, array.length(), "minItems", "maxItems", at);
        }
        if (value instanceof String) {
            String text = (String)value; bound(schema, text.codePointCount(0, text.length()), "minLength", "maxLength", at);
            if (schema.has("pattern") && !safePattern(schema.getString("pattern"), at).matcher(text).find()) fail(at, "String does not match the schema pattern");
            if (schema.has("format") && !format(schema.getString("format"), text)) fail(at, "String does not match the schema format");
        }
        if (value instanceof Number) {
            BigDecimal n = new BigDecimal(value.toString());
            for (String key : Arrays.asList("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum")) if (schema.has(key)) {
                int compared = n.compareTo(new BigDecimal(schema.get(key).toString()));
                if (key.equals("minimum") && compared < 0 || key.equals("maximum") && compared > 0 || key.equals("exclusiveMinimum") && compared <= 0 || key.equals("exclusiveMaximum") && compared >= 0) fail(at, "Number is outside the schema bounds");
            }
            if (schema.has("multipleOf") && n.remainder(new BigDecimal(schema.get("multipleOf").toString())).compareTo(BigDecimal.ZERO) != 0) fail(at, "Number is not a multipleOf the schema value");
        }
    }
    private static void bound(JSONObject schema, int value, String min, String max, String at) { if (schema.has(min) && value < schema.optDouble(min) || schema.has(max) && value > schema.optDouble(max)) fail(at, "Generated value is outside the schema size bounds"); }
    private static boolean isType(String type, Object value) {
        if (type.equals("null")) return value == null || value == JSONObject.NULL;
        if (type.equals("object")) return value instanceof JSONObject; if (type.equals("array")) return value instanceof JSONArray;
        if (type.equals("string")) return value instanceof String; if (type.equals("boolean")) return value instanceof Boolean;
        if (!(value instanceof Number)) return false;
        return type.equals("number") || type.equals("integer") && new BigDecimal(value.toString()).stripTrailingZeros().scale() <= 0;
    }
    private static String canonical(Object value) throws Exception {
        if (value == null || value == JSONObject.NULL) return "null";
        if (value instanceof Number) return new BigDecimal(value.toString()).stripTrailingZeros().toPlainString();
        if (value instanceof JSONObject) { JSONObject object = (JSONObject)value; List<String> names = new ArrayList<>(); for (Iterator<String> it = object.keys(); it.hasNext();) names.add(it.next()); Collections.sort(names); StringBuilder out = new StringBuilder("{"); for (String name : names) out.append(JSONObject.quote(name)).append(':').append(canonical(object.get(name))).append(','); return out.append('}').toString(); }
        if (value instanceof JSONArray) { JSONArray array = (JSONArray)value; StringBuilder out = new StringBuilder("["); for (int i = 0; i < array.length(); i++) out.append(canonical(array.get(i))).append(','); return out.append(']').toString(); }
        return value instanceof String ? JSONObject.quote((String)value) : String.valueOf(value);
    }
    private static boolean format(String format, String value) {
        try {
            switch (format) {
                case "date-time": OffsetDateTime.parse(value); return true;
                case "date": LocalDate.parse(value); return true;
                case "time": OffsetTime.parse(value); return true;
                case "uuid": return UUID.fromString(value).toString().equalsIgnoreCase(value);
                case "uri": return new URI(value).isAbsolute(); case "uri-reference": new URI(value); return true;
                case "email": return value.matches("[^@\\s]+@[^@\\s]+\\.[^@\\s]+");
                case "hostname": return value.length() <= 253 && value.matches("(?i)[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?");
                case "ipv4": String[] parts = value.split("\\.", -1); if (parts.length != 4) return false; for (String part : parts) if (!part.matches("0|[1-9][0-9]{0,2}") || Integer.parseInt(part) > 255) return false; return true;
                case "ipv6": return value.contains(":") && value.matches("[0-9a-fA-F:.]+") && java.net.InetAddress.getByName(value) instanceof java.net.Inet6Address;
                default: return false;
            }
        } catch (Exception error) { return false; }
    }
}
