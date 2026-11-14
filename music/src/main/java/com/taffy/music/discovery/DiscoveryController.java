package com.taffy.music.discovery;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.taffy.music.common.Result;
import com.taffy.music.utils.MediaResponses;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;
import java.util.*;

@RestController
@RequestMapping("/discovery")
public class DiscoveryController {
    private final DiscoveryService service;
    private final ObjectMapper json;
    public DiscoveryController(DiscoveryService service, ObjectMapper mapper) {
        this.service = service;
        this.json = mapper.copy().enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION)
                .enable(com.fasterxml.jackson.databind.DeserializationFeature.FAIL_ON_TRAILING_TOKENS);
    }
    private static String requestId(HttpServletRequest request) {
        if (request.getAttribute("discoveryRequestId") == null)
            request.setAttribute("discoveryRequestId", UUID.randomUUID().toString());
        return request.getAttribute("discoveryRequestId").toString();
    }
    @PostMapping("/search")
    public ResponseEntity<?> search(HttpServletRequest request) throws java.io.IOException {
        String requestId = requestId(request);
        if (request.getContentType() == null || !request.getContentType().toLowerCase(Locale.ROOT).startsWith("application/json"))
            throw DiscoveryException.invalid();
        byte[] raw = request.getInputStream().readNBytes(8193);
        if (raw.length > 8192) throw new DiscoveryException(413, "request_too_large", "检索请求过大");
        DiscoveryQuery query;
        try { query = DiscoveryQuery.parse(json.readTree(raw)); }
        catch (DiscoveryException e) { throw e; }
        catch (Exception e) { throw DiscoveryException.invalid(); }
        Map<String, Object> result = service.search(query); result.put("request_id", requestId);
        return ResponseEntity.ok().header("Cache-Control", "private, no-store").header("Vary", "Authorization")
                .body(Result.success(result));
    }
    @GetMapping("/tracks/{id}/media")
    public ResponseEntity<?> media(@PathVariable String id, @RequestParam(required = false) String content_md5,
                                    @RequestParam(required = false) String content_sha256) {
        var preview = service.preview(id, content_md5, content_sha256);
        return MediaResponses.file(preview.path(), preview.title(), MediaType.parseMediaType("audio/mpeg"), false);
    }
    @RequestMapping({"/**", ""})
    public ResponseEntity<?> unknown() {
        throw new DiscoveryException(404, "not_found", "检索接口不存在");
    }
    @ExceptionHandler(Exception.class)
    public ResponseEntity<?> error(Exception error, HttpServletRequest request) {
        int status = 500; String kind = "discovery_error", message = "检索请求处理失败";
        if (error instanceof DiscoveryException e) { status = e.status; kind = e.kind; message = e.getMessage(); }
        else if (error instanceof ResponseStatusException e) {
            status = e.getStatusCode().value();
            kind = status == 404 ? "media_unavailable" : status == 401 ? "unauthorized" : "access_denied";
            message = status == 404 ? "资源不可用" : "账号不可用";
        }
        Result<Object> body = Result.error(status, message);
        body.setData(Map.of("request_id", requestId(request), "error_type", kind));
        return ResponseEntity.status(status).header("Cache-Control", "private, no-store").header("Vary", "Authorization").body(body);
    }
}
