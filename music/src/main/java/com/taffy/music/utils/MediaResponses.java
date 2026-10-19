package com.taffy.music.utils;

import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;

import java.nio.charset.StandardCharsets;
import java.nio.file.Path;

public final class MediaResponses {
    private MediaResponses() {}

    public static ResponseEntity<Resource> file(Path path, String name, MediaType type, boolean attachment) {
        return file(path, name, type, attachment, null);
    }

    public static ResponseEntity<Resource> file(Path path, String name, MediaType type, boolean attachment, Long rate) {
        Resource resource = rate == null ? new FileSystemResource(path) : new FileSystemResource(path) {
            @Override public java.io.InputStream getInputStream() throws java.io.IOException {
                if (rate <= 0) throw new java.io.IOException("Invalid download rate");
                return new java.io.FilterInputStream(super.getInputStream()) {
                    private final long started = System.nanoTime();
                    private long transferred;
                    private void throttle(int count) throws java.io.IOException {
                        if (count <= 0) return;
                        transferred += count;
                        long wait = (long) (transferred * 1_000_000_000.0 / rate) - (System.nanoTime() - started);
                        if (wait > 0) {
                            try { java.util.concurrent.TimeUnit.NANOSECONDS.sleep(wait); }
                            catch (InterruptedException e) {
                                Thread.currentThread().interrupt();
                                throw new java.io.InterruptedIOException("Download interrupted");
                            }
                        }
                    }
                    @Override public int read() throws java.io.IOException {
                        int value = in.read(); throttle(value < 0 ? 0 : 1); return value;
                    }
                    @Override public int read(byte[] bytes, int offset, int length) throws java.io.IOException {
                        int count = in.read(bytes, offset, length); throttle(count); return count;
                    }
                };
            }
        };
        return ResponseEntity.ok()
                .contentType(type)
                .header(HttpHeaders.CONTENT_DISPOSITION, (attachment ? ContentDisposition.attachment() : ContentDisposition.inline())
                        .filename(name, StandardCharsets.UTF_8).build().toString())
                .header(HttpHeaders.CACHE_CONTROL, "private, no-store")
                .header(HttpHeaders.VARY, "Authorization")
                .header("X-Content-Type-Options", "nosniff")
                .body(resource);
    }
}
