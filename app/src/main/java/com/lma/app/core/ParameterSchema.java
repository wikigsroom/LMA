package com.lma.app.core;

import org.json.JSONArray;
import org.json.JSONObject;
import java.util.*;

/** Recipe limits, independent of device resource estimates. Produces an effective snapshot. */
public final class ParameterSchema {
    private final JSONObject schema, fields;
    public ParameterSchema(JSONObject value) {
        schema = DataFiles.copy(value); fields = schema.optJSONObject("fields") == null ? new JSONObject() : schema.optJSONObject("fields");
        try {
            if (fields.length() > 64) throw new IllegalArgumentException("Too many parameter fields");
            if (schema.has("version") && schema.getInt("version") < 1) throw new IllegalArgumentException("Invalid schema version");
            for (Iterator<String> it = fields.keys(); it.hasNext();) {
                String key = ModelBundle.key(it.next()); JSONObject field = fields.getJSONObject(key);
                String type = field.getString("type");
                if (!Arrays.asList("integer", "number", "string", "enum", "boolean").contains(type)) throw new IllegalArgumentException("Unknown parameter type");
                if (!field.has("default")) throw new IllegalArgumentException("Missing parameter default");
                if (field.has("minimum") && !Double.isFinite(field.getDouble("minimum")) || field.has("maximum") && !Double.isFinite(field.getDouble("maximum"))) throw new IllegalArgumentException("Non-finite parameter limit");
                if (field.has("minimum") && field.has("maximum") && field.getDouble("minimum") > field.getDouble("maximum")) throw new IllegalArgumentException("Reversed parameter limits");
                if (field.has("multipleOf") && (!Double.isFinite(field.getDouble("multipleOf")) || field.getDouble("multipleOf") <= 0)) throw new IllegalArgumentException("Invalid parameter alignment");
                if (field.has("alignmentOrigin") && !Double.isFinite(field.getDouble("alignmentOrigin"))) throw new IllegalArgumentException("Invalid alignment origin");
                if (type.equals("integer")) for (String limit : Arrays.asList("minimum", "maximum", "multipleOf", "alignmentOrigin")) if (field.has(limit) && field.getDouble(limit) != Math.floor(field.getDouble(limit))) throw new IllegalArgumentException("Integer parameters require integer limits");
                if (field.has("maxLength") && (field.getInt("maxLength") < 0 || field.getInt("maxLength") > 16000)) throw new IllegalArgumentException("Invalid text length limit");
                if (type.equals("enum") && (field.optJSONArray("values") == null || field.getJSONArray("values").length() == 0)) throw new IllegalArgumentException("Empty enum");
            }
            JSONArray shapes = schema.optJSONArray("allowedShapes");
            if (shapes != null) for (int i = 0; i < shapes.length(); i++) {
                JSONObject shape = shapes.getJSONObject(i);
                if (shape.length() == 0) throw new IllegalArgumentException("Empty compiled shape");
                for (Iterator<String> it = shape.keys(); it.hasNext();) {
                    String key = it.next();
                    if (!fields.has(key) || !Arrays.asList("integer", "number").contains(fields.getJSONObject(key).getString("type")) || !Double.isFinite(shape.getDouble(key))) throw new IllegalArgumentException("Invalid compiled shape field");
                }
            }
            normalize(new JSONObject(), new JSONObject());
        } catch (Exception error) { throw new IllegalArgumentException("Invalid parameter schema: " + error.getMessage(), error); }
    }
    public JSONObject json() { return DataFiles.copy(schema); }
    public JSONObject normalize(JSONObject defaults, JSONObject changes) throws Exception {
        for (Iterator<String> it = changes.keys(); it.hasNext();) if (!fields.has(it.next())) throw new IllegalArgumentException("Unknown model parameter");
        JSONObject effective = new JSONObject(); JSONArray adjustments = new JSONArray();
        for (Iterator<String> it = fields.keys(); it.hasNext();) {
            String key = it.next(); JSONObject f = fields.getJSONObject(key); String type = f.getString("type");
            Object requested = changes.has(key) ? changes.get(key) : defaults.has(key) ? defaults.get(key) : f.get("default"); Object result = requested;
            if (type.equals("integer") || type.equals("number")) {
                double numeric;
                try { numeric = Double.parseDouble(String.valueOf(requested)); } catch (Exception error) { throw new IllegalArgumentException(key + " needs a number"); }
                if (!Double.isFinite(numeric) || Math.abs(numeric) > 9007199254740991d) throw new IllegalArgumentException(key + " needs a finite number");
                if (type.equals("integer")) numeric = Math.floor(numeric);
                if (f.has("minimum")) numeric = Math.max(numeric, f.getDouble("minimum"));
                if (f.has("maximum")) numeric = Math.min(numeric, f.getDouble("maximum"));
                if (f.has("multipleOf")) { double step = f.getDouble("multipleOf"), origin = f.optDouble("alignmentOrigin", 0); numeric = origin + Math.floor((numeric - origin) / step) * step; }
                if (f.has("minimum") && numeric < f.getDouble("minimum")) throw new IllegalArgumentException(key + " has no aligned value inside its limits");
                if (type.equals("integer")) result = Long.valueOf((long) numeric); else result = Double.valueOf(numeric);
                if (numeric != Double.parseDouble(String.valueOf(requested))) adjustments.put(new JSONObject().put("field", key).put("requested", requested).put("effective", result).put("reason", "recipe_limit_or_alignment"));
            } else if (type.equals("string")) {
                if (!(requested instanceof String) || ((String) requested).length() > f.optInt("maxLength", 16000)) throw new IllegalArgumentException(key + " is too long or not text");
            } else if (type.equals("boolean")) {
                if (!(requested instanceof Boolean)) throw new IllegalArgumentException(key + " needs true or false");
            } else {
                boolean found = false; JSONArray values = f.getJSONArray("values");
                for (int i = 0; i < values.length(); i++) if (values.get(i).equals(requested)) found = true;
                if (!found) throw new IllegalArgumentException(key + " has an unsupported selection");
            }
            effective.put(key, result);
        }
        JSONArray shapes = schema.optJSONArray("allowedShapes");
        if (shapes != null && shapes.length() > 0) {
            boolean match = false;
            for (int i = 0; i < shapes.length(); i++) {
                JSONObject shape = shapes.getJSONObject(i); boolean current = true;
                for (Iterator<String> it = shape.keys(); it.hasNext();) { String key = it.next(); if (!effective.has(key) || effective.getDouble(key) != shape.getDouble(key)) current = false; }
                match |= current;
            }
            if (!match) throw new IllegalArgumentException("Width, height and frames must match one complete compiled shape");
        }
        return new JSONObject().put("values", effective).put("adjustments", adjustments).put("schemaVersion", schema.optInt("version", 1));
    }
}
