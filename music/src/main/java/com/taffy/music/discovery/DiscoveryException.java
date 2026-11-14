package com.taffy.music.discovery;

public class DiscoveryException extends RuntimeException {
    public final int status;
    public final String kind;
    public DiscoveryException(int status, String kind, String message) {
        super(message);
        this.status = status;
        this.kind = kind;
    }
    public static DiscoveryException invalid() {
        return new DiscoveryException(400, "invalid_input", "检索参数无效");
    }
    public static DiscoveryException unavailable() {
        return new DiscoveryException(503, "search_unavailable", "检索服务暂不可用");
    }
}
