package com.taffy.music.discovery;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Component;
import java.net.URI;
import java.net.http.*;
import java.time.Duration;
import java.io.InputStream;
import java.util.Set;

@Component
public class DiscoveryClient {
    private final DiscoveryProperties properties;
    private final ObjectMapper json;
    private final HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(2))
            .followRedirects(HttpClient.Redirect.NEVER).build();
    public DiscoveryClient(DiscoveryProperties properties, ObjectMapper mapper) {
        this.properties = properties;
        this.json = mapper.copy().enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION)
                .enable(com.fasterxml.jackson.databind.DeserializationFeature.FAIL_ON_TRAILING_TOKENS);
    }
    public JsonNode search(JsonNode body) {
        try {
            URI base = URI.create(properties.getUrl());
            if (!"http".equals(base.getScheme()) || !Set.of("127.0.0.1", "localhost", "[::1]", "::1").contains(base.getHost())
                    || base.getPort() < 1 || base.getUserInfo() != null || base.getQuery() != null || base.getFragment() != null
                    || !(base.getPath().isEmpty() || base.getPath().equals("/")) || properties.getSecret().length() < 32)
                throw DiscoveryException.unavailable();
            byte[] encoded = json.writeValueAsBytes(body);
            if (encoded.length > 2 * 1024 * 1024) throw DiscoveryException.unavailable();
            var request = HttpRequest.newBuilder(base.resolve("/internal/search")).timeout(Duration.ofSeconds(8))
                    .header("Content-Type", "application/json").header("Authorization", "Bearer " + properties.getSecret())
                    .POST(HttpRequest.BodyPublishers.ofByteArray(encoded)).build();
            var response = client.send(request, HttpResponse.BodyHandlers.ofInputStream());
            try (InputStream input = response.body()) {
                byte[] raw = input.readNBytes(65537);
                if (raw.length > 65536) throw DiscoveryException.unavailable();
                JsonNode data = json.readTree(raw);
                if (response.statusCode() == 400 && data != null && "query_tokens_exceeded".equals(data.path("error_type").asText()))
                    throw new DiscoveryException(400, "query_tokens_exceeded", "完整描述超过256个模型token，请缩短描述");
                if (response.statusCode() == 503 && data != null && "fixture_query_unavailable".equals(data.path("error_type").asText()))
                    throw new DiscoveryException(503, "fixture_query_unavailable", "当前为合成联调，请使用已配置的固定示例");
                if (response.statusCode() != 200 || data == null) throw DiscoveryException.unavailable();
                return data;
            }
        } catch (DiscoveryException e) { throw e; }
        catch (InterruptedException e) { Thread.currentThread().interrupt(); throw DiscoveryException.unavailable(); }
        catch (Exception e) { throw DiscoveryException.unavailable(); }
    }
}
