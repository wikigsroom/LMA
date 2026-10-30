package com.lma.app.core;

import org.json.JSONArray;
import org.json.JSONObject;
import java.util.*;

/** Recipe limits, independent of device resource estimates. Produces an effective snapshot. */
public final class ParameterSchema {
    private final JSONObject schema, fields;
    private static void choices(JSONObject field, String type) throws Exception {
        JSONArray choices = field.getJSONArray("choices");
        if (!Arrays.asList("integer", "number").contains(type) || choices.length() > 128) throw new IllegalArgumentException("Invalid numeric parameter choices");
        Set<Double> values = new HashSet<>();
        for (int i = 0; i < choices.length(); i++) {
            JSONObject choice = choices.getJSONObject(i); Object raw = choice.get("value"); String label = choice.getString("label");
            if (choice.length() != 2 || !(raw instanceof Number) || label.isEmpty() || label.length() > 80 || !label.equals(label.trim())) throw new IllegalArgumentException("Invalid parameter choice label/value");
            for (int c = 0; c < label.length(); c++) if (Character.isISOControl(label.charAt(c))) throw new IllegalArgumentException("Parameter choice label contains controls");
            double value = ((Number) raw).doubleValue();
            if (!Double.isFinite(value) || Math.abs(value) > 9007199254740991d || type.equals("integer") && value != Math.floor(value) || !values.add(value == 0 ? 0d : value)) throw new IllegalArgumentException("Invalid or duplicate parameter choice value");
            if (field.has("minimum") && value < field.getDouble("minimum") || field.has("maximum") && value > field.getDouble("maximum")) throw new IllegalArgumentException("Parameter choice exceeds declared bounds");
            if (field.has("multipleOf")) { double steps = (value - field.optDouble("alignmentOrigin", 0)) / field.getDouble("multipleOf"); if (Math.abs(steps - Math.rint(steps)) > 1e-9) throw new IllegalArgumentException("Unaligned parameter choice"); }
        }
    }
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
                if (field.has("choices")) choices(field, type);
                if (field.has("maximumFrom")) {
                    JSONObject bound = field.getJSONObject("maximumFrom"); String source = ModelBundle.key(bound.getString("field"));
                    if (!Arrays.asList("integer", "number").contains(type) || source.equals(key) || !fields.has(source) || !Arrays.asList("integer", "number").contains(fields.getJSONObject(source).getString("type"))) throw new IllegalArgumentException("Invalid dependent parameter bound");
                    for (Iterator<String> keys = bound.keys(); keys.hasNext();) if (!Arrays.asList("field", "offset").contains(keys.next())) throw new IllegalArgumentException("Unknown dependent bound field");
                    if (bound.length() > 2 || !Double.isFinite(bound.optDouble("offset", 0)) || type.equals("integer") && bound.optDouble("offset", 0) != Math.floor(bound.optDouble("offset", 0))) throw new IllegalArgumentException("Invalid dependent bound offset");
                }
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
    private void dependent(String key, JSONObject values, JSONArray changes, Set<String> done, Set<String> visiting) throws Exception {
        if (done.contains(key)) return;
        if (!visiting.add(key)) throw new IllegalArgumentException("Cyclic parameter bounds");
        JSONObject field = fields.getJSONObject(key), bound = field.optJSONObject("maximumFrom");
        if (bound != null) {
            String source = bound.getString("field"); dependent(source, values, changes, done, visiting);
            double original = values.getDouble(key), value = Math.min(original, values.getDouble(source) + bound.optDouble("offset", 0));
            if (field.getString("type").equals("integer")) value = Math.floor(value);
            if (field.has("multipleOf")) { double step = field.getDouble("multipleOf"), origin = field.optDouble("alignmentOrigin", 0); value = origin + Math.floor((value - origin) / step) * step; }
            if (!Double.isFinite(value) || field.has("minimum") && value < field.getDouble("minimum")) throw new IllegalArgumentException("Dependent parameter bounds have no legal value");
            if (value != original) {
                Object result = field.getString("type").equals("integer") ? (Object) Long.valueOf((long) value) : Double.valueOf(value);
                changes.put(new JSONObject().put("field", key).put("requested", values.get(key)).put("effective", result).put("reason", "dependent_parameter_limit")); values.put(key, result);
            }
        }
        visiting.remove(key); done.add(key);
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
        Set<String> bounded = new HashSet<>();
        for (Iterator<String> it = fields.keys(); it.hasNext();) dependent(it.next(), effective, adjustments, bounded, new HashSet<>());
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
