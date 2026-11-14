package com.taffy.music.discovery;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.*;

public record DiscoveryQuery(String text, String mode, int topK, Long categoryId, List<Long> tagIds, boolean allTags) {
    public static void fields(JsonNode node, Set<String> required, Set<String> optional) {
        if (node == null || !node.isObject()) throw DiscoveryException.invalid();
        Set<String> actual = new HashSet<>();
        node.fieldNames().forEachRemaining(actual::add);
        Set<String> allowed = new HashSet<>(required); allowed.addAll(optional);
        if (!actual.containsAll(required) || !allowed.containsAll(actual)) throw DiscoveryException.invalid();
    }
    public static long id(String value) {
        if (value == null || !value.matches("[1-9][0-9]{0,18}")) throw DiscoveryException.invalid();
        try { return Long.parseLong(value); }
        catch (NumberFormatException e) { throw DiscoveryException.invalid(); }
    }
    private static String string(JsonNode value) {
        if (value == null || !value.isTextual()) throw DiscoveryException.invalid();
        return value.textValue();
    }
    public static DiscoveryQuery parse(JsonNode body) {
        fields(body, Set.of("query"), Set.of("filters", "retrieval_mode", "top_k"));
        JsonNode query = body.get("query");
        fields(query, Set.of("kind", "text"), Set.of());
        if (!"text".equals(string(query.get("kind")))) throw DiscoveryException.invalid();
        String text = string(query.get("text")).strip();
        if (text.isEmpty() || text.codePointCount(0, text.length()) > 1000) throw DiscoveryException.invalid();
        String mode = body.has("retrieval_mode") ? string(body.get("retrieval_mode")) : "segment";
        if (!Set.of("segment", "whole_track").contains(mode)) throw DiscoveryException.invalid();
        int top = 10;
        if (body.has("top_k")) {
            JsonNode value = body.get("top_k");
            if (!value.isIntegralNumber() || !value.canConvertToInt()) throw DiscoveryException.invalid();
            top = value.intValue();
        }
        if (top < 1 || top > 20) throw DiscoveryException.invalid();
        Long category = null; LinkedHashSet<Long> tags = new LinkedHashSet<>(); boolean all = true;
        if (body.has("filters")) {
            JsonNode filters = body.get("filters");
            fields(filters, Set.of(), Set.of("category_id", "tag_ids", "tag_match"));
            if (filters.hasNonNull("category_id")) category = id(string(filters.get("category_id")));
            if (filters.has("tag_ids")) {
                JsonNode ids = filters.get("tag_ids");
                if (!ids.isArray() || ids.size() > 32) throw DiscoveryException.invalid();
                for (JsonNode value : ids) tags.add(id(string(value)));
            }
            if (filters.has("tag_match")) {
                String match = string(filters.get("tag_match"));
                if (!Set.of("all", "any").contains(match)) throw DiscoveryException.invalid();
                all = match.equals("all");
            }
        }
        return new DiscoveryQuery(text, mode, top, category, List.copyOf(tags), all);
    }
}
