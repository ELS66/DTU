package com.dtu.iot.protocol;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

/** Decodes telemetry v1. Gateway identity comes from the authenticated MQTT session. */
public record TelemetryFrame(long configRevision, UUID bootId, long sequence,
                             long sampleTimeMs, boolean replayed, boolean timeTrusted,
                             List<Point> points) {
    private static final int HEADER_SIZE = 47;
    private static final int MAX_FRAME_SIZE = 4096;
    private static final int POINT_HEADER_SIZE = 10;

    public TelemetryFrame {
        points = List.copyOf(points);
    }

    public record Point(int pointCode, RawType rawType, Quality quality,
                        int sampleOffsetMs, Object value) {
        public long sampledAt(long frameTimeMs) {
            return Math.addExact(frameTimeMs, sampleOffsetMs);
        }
    }

    public enum RawType {
        UINT16(1, 2), INT16(2, 2), UINT32(3, 4), INT32(4, 4), FLOAT32(5, 4), BOOL(6, 1);

        private final int code;
        private final int width;

        RawType(int code, int width) {
            this.code = code;
            this.width = width;
        }

        public static RawType fromCode(int code) {
            for (RawType type : values()) {
                if (type.code == code) return type;
            }
            throw new IllegalArgumentException("unknown raw type: " + code);
        }
    }

    public enum Quality {
        GOOD(0), READ_TIMEOUT(1), MODBUS_ERROR(2), INVALID_VALUE(3);

        private final int code;

        Quality(int code) {
            this.code = code;
        }

        public static Quality fromCode(int code) {
            for (Quality quality : values()) {
                if (quality.code == code) return quality;
            }
            throw new IllegalArgumentException("unknown quality: " + code);
        }
    }

    public static TelemetryFrame decode(byte[] frame) {
        if (frame == null || frame.length < HEADER_SIZE || frame.length > MAX_FRAME_SIZE) {
            throw new IllegalArgumentException("invalid frame length");
        }
        ByteBuffer data = ByteBuffer.wrap(frame).order(ByteOrder.BIG_ENDIAN);
        if (data.get() != 'D' || data.get() != 'T' || data.get() != 1 || data.get() != 1) {
            throw new IllegalArgumentException("invalid telemetry v1 header");
        }
        long payloadLength = Integer.toUnsignedLong(data.getInt());
        if (payloadLength != frame.length - HEADER_SIZE) {
            throw new IllegalArgumentException("payload length mismatch");
        }
        long revision = Integer.toUnsignedLong(data.getInt());
        UUID bootId = new UUID(data.getLong(), data.getLong());
        long sequence = data.getLong();
        long sampleTime = data.getLong();
        int flags = Byte.toUnsignedInt(data.get());
        int pointCount = Short.toUnsignedInt(data.getShort());
        boolean timeTrusted = (flags & 2) != 0;
        if (revision == 0 || sequence <= 0 || sampleTime < 0 || flags > 3
                || pointCount < 1 || pointCount > 128 || timeTrusted != (sampleTime > 0)) {
            throw new IllegalArgumentException("invalid telemetry metadata");
        }
        List<Point> points = new ArrayList<>(pointCount);
        Set<Integer> seenCodes = new HashSet<>();
        for (int i = 0; i < pointCount; i++) {
            if (data.remaining() < POINT_HEADER_SIZE) {
                throw new IllegalArgumentException("truncated point header");
            }
            int pointCode = Short.toUnsignedInt(data.getShort());
            RawType rawType = RawType.fromCode(Byte.toUnsignedInt(data.get()));
            Quality quality = Quality.fromCode(Byte.toUnsignedInt(data.get()));
            int sampleOffset = data.getInt();
            int valueLength = Short.toUnsignedInt(data.getShort());
            int requiredLength = quality == Quality.GOOD ? rawType.width : 0;
            if (pointCode == 0 || !seenCodes.add(pointCode) || valueLength != requiredLength
                    || data.remaining() < valueLength || (!timeTrusted && sampleOffset != 0)) {
                throw new IllegalArgumentException("invalid point metadata");
            }
            if (timeTrusted && Math.addExact(sampleTime, sampleOffset) < 0) {
                throw new IllegalArgumentException("invalid point sample time");
            }
            Object value = quality == Quality.GOOD ? readValue(data, rawType) : null;
            points.add(new Point(pointCode, rawType, quality, sampleOffset, value));
        }
        if (data.hasRemaining()) {
            throw new IllegalArgumentException("unexpected trailing bytes");
        }
        return new TelemetryFrame(revision, bootId, sequence, sampleTime,
                (flags & 1) != 0, timeTrusted, points);
    }

    private static Object readValue(ByteBuffer data, RawType rawType) {
        return switch (rawType) {
            case UINT16 -> Short.toUnsignedInt(data.getShort());
            case INT16 -> data.getShort();
            case UINT32 -> Integer.toUnsignedLong(data.getInt());
            case INT32 -> data.getInt();
            case FLOAT32 -> {
                float value = data.getFloat();
                if (!Float.isFinite(value)) throw new IllegalArgumentException("non-finite float");
                yield value;
            }
            case BOOL -> {
                int value = Byte.toUnsignedInt(data.get());
                if (value > 1) throw new IllegalArgumentException("invalid boolean");
                yield value == 1;
            }
        };
    }
}
