package com.taffy.music.discovery;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Data
@Component
@ConfigurationProperties(prefix = "discovery")
public class DiscoveryProperties {
    private boolean enabled = false;
    private boolean allowSynthetic = false;
    private String url = "http://127.0.0.1:8091";
    private String secret = "";
    private String indexVersion = "";
    private String modelVersion = "";
}
