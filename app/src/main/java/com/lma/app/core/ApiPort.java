package com.lma.app.core;

/** Public API preference defaults, independent of private native-engine ports. */
public final class ApiPort {
    public static final int DEFAULT = 52187;
    public static final int DEFAULTS_VERSION = 1;
    private ApiPort() {}

    /** Move the former default once; preserve valid custom ports and later edits. */
    public static int afterUpgrade(int savedPort, int defaultsVersion) {
        if (savedPort < 1024 || savedPort > 65535) return DEFAULT;
        if (defaultsVersion < DEFAULTS_VERSION && savedPort == 8080) return DEFAULT;
        return savedPort;
    }
}
