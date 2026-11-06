package com.lma.app.core;

/** A client-visible field error. Never includes request contents or credentials. */
public final class RequestError extends IllegalArgumentException {
    public final String param, code;
    public RequestError(String param, String message) { this(param, "invalid_request_error", message); }
    public RequestError(String param, String code, String message) { super(message); this.param = param; this.code = code; }
}
