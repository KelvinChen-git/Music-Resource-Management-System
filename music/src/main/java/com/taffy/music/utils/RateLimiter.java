package com.taffy.music.utils;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

/**
 * 限速器工具类
 */
public class RateLimiter {
    private final long bytesPerSecond;
    private long bytesRead;
    private long lastCheckTime;

    public RateLimiter(long bytesPerSecond) {
        this.bytesPerSecond = bytesPerSecond;
        this.bytesRead = 0;
        this.lastCheckTime = System.currentTimeMillis();
    }

    /**
     * 限速拷贝流
     */
    public void copy(InputStream input, OutputStream output, byte[] buffer) throws IOException {
        int bytesRead;
        while ((bytesRead = input.read(buffer)) != -1) {
            output.write(buffer, 0, bytesRead);
            output.flush();
            throttle(bytesRead);
        }
    }

    /**
     * 限速控制
     */
    private void throttle(int bytes) {
        this.bytesRead += bytes;
        long now = System.currentTimeMillis();
        long timePassedMillis = now - lastCheckTime;

        // 每秒检查一次
        if (timePassedMillis >= 1000) {
            // 重置计数
            this.bytesRead = bytes;
            this.lastCheckTime = now;
            return;
        }

        // 计算当前速率
        double currentBytesPerSecond = (this.bytesRead * 1000.0) / timePassedMillis;

        // 如果当前速率超过限制，则等待
        if (currentBytesPerSecond > this.bytesPerSecond) {
            long needToWaitMillis = (long) ((this.bytesRead * 1000.0) / this.bytesPerSecond - timePassedMillis);
            try {
                Thread.sleep(Math.max(needToWaitMillis, 0));
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            // 重置计数
            this.bytesRead = 0;
            this.lastCheckTime = System.currentTimeMillis();
        }
    }
}