package com.taffy.music.discovery;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.taffy.music.domain.*;
import com.taffy.music.mapper.DiscoveryTagMapper;
import com.taffy.music.service.*;
import org.springframework.stereotype.Service;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;

@Service
public class DiscoveryService {
    private static final long MAX_BYTES = 30L * 1024 * 1024;
    private final MusicResourceService music;
    private final FileUploadService uploads;
    private final MediaAccessService access;
    private final DiscoveryTagMapper tags;
    private final DiscoveryClient worker;
    private final DiscoveryProperties config;
    private final ObjectMapper json;
    private record Visible(MusicResources music, FileUpload upload) {}
    public record Preview(Path path, String title) {}

    public DiscoveryService(MusicResourceService music, FileUploadService uploads, MediaAccessService access,
                            DiscoveryTagMapper tags, DiscoveryClient worker, DiscoveryProperties config, ObjectMapper json) {
        this.music = music; this.uploads = uploads; this.access = access; this.tags = tags;
        this.worker = worker; this.config = config; this.json = json;
    }
    private void enabled() {
        if (!config.isEnabled() || config.getIndexVersion().isBlank() || config.getModelVersion().isBlank())
            throw DiscoveryException.unavailable();
    }
    private static boolean eligible(MusicResources row) {
        return row != null && row.getMusicid() != null && row.getMusicid() > 0
                && Boolean.FALSE.equals(row.getIsDeleted()) && "approved".equals(row.getApprovalStatus());
    }
    private Map<String, Visible> visible(DiscoveryQuery q) { return visible(q, null); }
    private Map<String, Visible> visible(DiscoveryQuery q, Long trackId) {
        List<Long> matched = null;
        if (!q.tagIds().isEmpty()) {
            matched = tags.matching(q.tagIds(), q.allTags(), q.tagIds().size());
            if (matched == null || matched.isEmpty()) return Map.of();
        }
        var where = new LambdaQueryWrapper<MusicResources>().eq(MusicResources::getIsDeleted, false)
                .eq(MusicResources::getApprovalStatus, "approved");
        if (trackId != null) where.eq(MusicResources::getMusicid, trackId);
        if (q.categoryId() != null) where.eq(MusicResources::getCategoryid, q.categoryId());
        if (matched != null) where.in(MusicResources::getMusicid, matched);
        List<MusicResources> rows = music.list(where.orderByAsc(MusicResources::getMusicid).last("LIMIT 5001"));
        if (rows.size() > 5000) throw new DiscoveryException(503, "catalog_limit", "首版检索候选超出上限，请缩小筛选范围");
        if (rows.isEmpty()) return Map.of();
        List<String> paths = rows.stream().map(MusicResources::getFilePath).filter(Objects::nonNull).distinct().toList();
        if (paths.isEmpty()) return Map.of();
        List<FileUpload> files = uploads.list(new LambdaQueryWrapper<FileUpload>().eq(FileUpload::getStatus, 1)
                .eq(FileUpload::getDeleted, false).in(FileUpload::getFilePath, paths));
        Map<String, List<FileUpload>> byPath = new HashMap<>();
        for (FileUpload file : files) {
            if (!Integer.valueOf(1).equals(file.getStatus()) || !Boolean.FALSE.equals(file.getDeleted())
                    || file.getFileMd5() == null || !file.getFileMd5().matches("[a-f0-9]{32}")
                    || file.getFileSize() == null || file.getFileSize() < 1 || file.getFileSize() > MAX_BYTES
                    || !"mp3".equalsIgnoreCase(file.getFileType())) continue;
            byPath.computeIfAbsent(file.getFilePath(), ignored -> new ArrayList<>()).add(file);
        }
        Map<String, Visible> result = new LinkedHashMap<>();
        for (MusicResources row : rows) {
            List<FileUpload> bound = byPath.getOrDefault(row.getFilePath(), List.of());
            if (eligible(row) && (trackId == null || trackId.equals(row.getMusicid())) && (q.categoryId() == null || q.categoryId().equals(row.getCategoryid()))
                    && (matched == null || matched.contains(row.getMusicid())) && bound.size() == 1)
                result.put(row.getMusicid().toString(), new Visible(row, bound.get(0)));
        }
        return result;
    }
    private static String string(JsonNode row, String key, String pattern) {
        JsonNode value = row.get(key);
        if (value == null || !value.isTextual() || !value.textValue().matches(pattern)) throw DiscoveryException.unavailable();
        return value.textValue();
    }
    private static long integer(JsonNode row, String key, long min, long max) {
        JsonNode value = row.get(key);
        if (value == null || !value.isIntegralNumber() || !value.canConvertToLong()
                || value.longValue() < min || value.longValue() > max) throw DiscoveryException.unavailable();
        return value.longValue();
    }
    private static double score(JsonNode row, String key) {
        JsonNode value = row.get(key);
        if (value == null || !value.isNumber() || !Double.isFinite(value.doubleValue())
                || Math.abs(value.doubleValue()) > 1.00001) throw DiscoveryException.unavailable();
        return value.doubleValue();
    }
    public Map<String, Object> search(DiscoveryQuery query) {
        long started = System.nanoTime(); access.requireViewer(); enabled();
        Map<String, Visible> before = visible(query);
        ObjectNode request = json.createObjectNode();
        request.put("query_text", query.text()); request.put("retrieval_mode", query.mode()); request.put("top_k", query.topK());
        request.put("index_version", config.getIndexVersion()); request.put("model_version", config.getModelVersion());
        var allowed = request.putArray("allowed_tracks");
        before.forEach((id, row) -> allowed.addObject().put("track_id", id)
                .put("content_md5", row.upload().getFileMd5()).put("content_bytes", row.upload().getFileSize()));
        JsonNode response;
        try { response = worker.search(request); }
        catch (DiscoveryException e) { throw e; }
        catch (Exception e) { throw DiscoveryException.unavailable(); }
        if (response == null) throw DiscoveryException.unavailable();
        if (!config.getIndexVersion().equals(response.path("index_version").asText())
                || !config.getModelVersion().equals(response.path("model_version").asText())
                || !query.mode().equals(response.path("retrieval_mode").asText())) throw DiscoveryException.unavailable();
        String kind = response.path("engine_kind").asText();
        if (!kind.equals("clap_identity") && !(kind.equals("synthetic_fixture") && config.isAllowSynthetic()))
            throw DiscoveryException.unavailable();
        JsonNode candidates = response.get("results");
        if (candidates == null || !candidates.isArray() || candidates.size() > query.topK()) throw DiscoveryException.unavailable();
        access.requireViewer(); Map<String, Visible> current = visible(query);
        List<Map<String, Object>> results = new ArrayList<>(); Set<String> seen = new HashSet<>();
        for (JsonNode candidate : candidates) {
            String id = string(candidate, "track_id", "[1-9][0-9]{0,18}");
            try { DiscoveryQuery.id(id); } catch (DiscoveryException e) { throw DiscoveryException.unavailable(); }
            if (!before.containsKey(id) || !seen.add(id)) throw DiscoveryException.unavailable();
            long duration = integer(candidate, "duration_ms", 1, Integer.MAX_VALUE);
            long bytes = integer(candidate, "content_bytes", 1, MAX_BYTES);
            String md5 = string(candidate, "content_md5", "[a-f0-9]{32}");
            String sha = string(candidate, "content_sha256", "[a-f0-9]{64}");
            double rankScore = score(candidate, "score");
            if (before.get(id).upload().getFileSize() != bytes || !before.get(id).upload().getFileMd5().equals(md5))
                throw DiscoveryException.unavailable();
            JsonNode clips = candidate.get("segments");
            if (clips == null || !clips.isArray() || clips.isEmpty() || clips.size() > 3) throw DiscoveryException.unavailable();
            List<Map<String, Object>> segments = new ArrayList<>(); Set<String> segmentIds = new HashSet<>();
            for (JsonNode clip : clips) {
                String sid = string(clip, "segment_id", "[A-Za-z0-9._:-]{1,100}");
                long start = integer(clip, "start_ms", 0, duration - 1), end = integer(clip, "end_ms", 1, duration);
                if (start >= end || !segmentIds.add(sid)) throw DiscoveryException.unavailable();
                for (Map<String, Object> earlier : segments)
                    if (Math.max(start, (long) earlier.get("start_ms")) < Math.min(end, (long) earlier.get("end_ms")))
                        throw DiscoveryException.unavailable();
                segments.add(Map.of("segment_id", sid, "start_ms", start, "end_ms", end, "score", score(clip, "score")));
            }
            Visible row = current.get(id);
            if (row == null || !row.upload().getFileMd5().equals(md5) || row.upload().getFileSize() != bytes) continue;
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("track_id", id); result.put("title", Objects.toString(row.music().getTitle(), ""));
            result.put("artist", Objects.toString(row.music().getArtist(), "")); result.put("duration_ms", duration);
            result.put("content_bytes", bytes); result.put("content_md5", md5); result.put("content_sha256", sha);
            result.put("score", rankScore); result.put("segments", segments);
            result.put("preview_url", "/api/discovery/tracks/" + id + "/media?content_md5=" + md5 + "&content_sha256=" + sha);
            results.add(result);
        }
        JsonNode timing = response.path("timings_ms");
        double encoding = scoreTime(timing, "query_encoding"), retrieval = scoreTime(timing, "retrieval");
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("index_version", config.getIndexVersion()); result.put("model_version", config.getModelVersion());
        result.put("engine_kind", kind); result.put("retrieval_mode", query.mode()); result.put("results", results);
        result.put("timings_ms", Map.of("query_encoding", encoding, "retrieval", retrieval, "total", (System.nanoTime() - started) / 1e6));
        return result;
    }
    private static double scoreTime(JsonNode row, String key) {
        JsonNode value = row.get(key);
        if (value == null || !value.isNumber() || !Double.isFinite(value.doubleValue()) || value.doubleValue() < 0)
            throw DiscoveryException.unavailable();
        return value.doubleValue();
    }
    public Preview preview(String id, String md5, String sha) {
        access.requireViewer(); enabled(); long tid = DiscoveryQuery.id(id);
        if (md5 == null || !md5.matches("[a-f0-9]{32}") || sha == null || !sha.matches("[a-f0-9]{64}"))
            throw DiscoveryException.invalid();
        var query = new DiscoveryQuery("preview", "segment", 1, null, List.of(), true);
        Visible row = visible(query, tid).get(id);
        if (row == null) throw MediaAccessService.unavailable();
        if (!row.upload().getFileMd5().equals(md5)) throw new DiscoveryException(409, "stale_content", "索引内容已过期");
        Path path = access.requirePath(row.music().getFilePath());
        try {
            if (Files.size(path) != row.upload().getFileSize()) throw new DiscoveryException(409, "stale_content", "索引内容已过期");
            MessageDigest hash = MessageDigest.getInstance("SHA-256");
            try (var stream = Files.newInputStream(path)) {
                byte[] buffer = new byte[65536]; int count;
                while ((count = stream.read(buffer)) != -1) hash.update(buffer, 0, count);
            }
            if (!HexFormat.of().formatHex(hash.digest()).equals(sha)) throw new DiscoveryException(409, "stale_content", "索引内容已过期");
        } catch (DiscoveryException e) { throw e; }
        catch (Exception e) { throw MediaAccessService.unavailable(); }
        access.requireViewer();
        Visible current = visible(query, tid).get(id);
        if (current == null || !Objects.equals(current.music().getFilePath(), row.music().getFilePath()))
            throw MediaAccessService.unavailable();
        if (!current.upload().getFileMd5().equals(md5) || current.upload().getFileSize() != row.upload().getFileSize().longValue())
            throw new DiscoveryException(409, "stale_content", "索引内容已过期");
        return new Preview(path, Objects.toString(current.music().getTitle(), "music") + ".mp3");
    }
}
