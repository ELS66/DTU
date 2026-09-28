import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.HashSet;
import java.util.HexFormat;
import java.util.Set;

/** Dependency-free Java verifier for the telemetry v1 golden vector. */
public final class TelemetryV1 {
    private static final int HEADER_SIZE = 47;
    private static final int MAX_FRAME = 4096;

    private TelemetryV1() {}

    public record Frame(long revision, long sequence, long sampleTimeMs,
                        boolean replayed, boolean timeTrusted, int pointCount,
                        int firstCode, Number firstValue) {}

    public static Frame decode(byte[] bytes) {
        if (bytes.length < HEADER_SIZE || bytes.length > MAX_FRAME) {
            throw new IllegalArgumentException("invalid frame length");
        }
        ByteBuffer b = ByteBuffer.wrap(bytes).order(ByteOrder.BIG_ENDIAN);
        if (b.get() != 0x44 || b.get() != 0x54 || b.get() != 1 || b.get() != 1) {
            throw new IllegalArgumentException("invalid header");
        }
        long payloadLength = Integer.toUnsignedLong(b.getInt());
        if (payloadLength != bytes.length - HEADER_SIZE) {
            throw new IllegalArgumentException("payload length mismatch");
        }
        long revision = Integer.toUnsignedLong(b.getInt());
        b.position(b.position() + 16); // boot ID
        long sequence = b.getLong();
        long sampleTime = b.getLong();
        int flags = Byte.toUnsignedInt(b.get());
        int count = Short.toUnsignedInt(b.getShort());
        if (revision == 0 || sequence <= 0 || sampleTime < 0 || (flags & ~3) != 0
                || count < 1 || count > 128 || ((flags & 2) != 0) != (sampleTime > 0)) {
            throw new IllegalArgumentException("invalid frame metadata");
        }
        Set<Integer> codes = new HashSet<>();
        Number firstValue = null;
        int firstCode = 0;
        for (int i = 0; i < count; i++) {
            if (b.remaining() < 10) {
                throw new IllegalArgumentException("truncated point");
            }
            int code = Short.toUnsignedInt(b.getShort());
            int rawType = Byte.toUnsignedInt(b.get());
            int quality = Byte.toUnsignedInt(b.get());
            int offset = b.getInt();
            int length = Short.toUnsignedInt(b.getShort());
            int expected = switch (rawType) {
                case 1, 2 -> 2;
                case 3, 4, 5 -> 4;
                case 6 -> 1;
                default -> throw new IllegalArgumentException("unknown raw type");
            };
            if (code == 0 || !codes.add(code) || quality > 3 ||
                    (sampleTime == 0 && offset != 0) ||
                    length != (quality == 0 ? expected : 0) || b.remaining() < length) {
                throw new IllegalArgumentException("invalid point");
            }
            Number value = null;
            if (quality == 0) {
                value = switch (rawType) {
                    case 1 -> Short.toUnsignedInt(b.getShort());
                    case 2 -> b.getShort();
                    case 3 -> Integer.toUnsignedLong(b.getInt());
                    case 4 -> b.getInt();
                    case 5 -> b.getFloat();
                    case 6 -> Byte.toUnsignedInt(b.get());
                    default -> throw new IllegalStateException();
                };
                if (rawType == 5 && !Float.isFinite(value.floatValue())) {
                    throw new IllegalArgumentException("non-finite float");
                }
                if (rawType == 6 && value.intValue() > 1) {
                    throw new IllegalArgumentException("invalid boolean");
                }
            }
            if (i == 0) {
                firstCode = code;
                firstValue = value;
            }
        }
        if (b.hasRemaining()) {
            throw new IllegalArgumentException("trailing data");
        }
        return new Frame(revision, sequence, sampleTime, (flags & 1) != 0,
                (flags & 2) != 0, count, firstCode, firstValue);
    }

    public static void main(String[] args) {
        String vector = "44540101000000170000000c000102030405060708090a0b0c0d0e0f"
                + "00000000000000070000019e70448800020002"
                + "000102000000000000020109"
                + "0002060000000032000101";
        Frame frame = decode(HexFormat.of().parseHex(vector));
        if (frame.revision() != 12 || frame.sequence() != 7 || frame.pointCount() != 2
                || frame.firstCode() != 1 || frame.firstValue().intValue() != 265) {
            throw new AssertionError("golden vector mismatch");
        }
        System.out.println("Telemetry v1 Java golden vector OK");
    }
}
