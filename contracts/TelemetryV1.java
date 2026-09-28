import com.dtu.iot.protocol.TelemetryFrame;
import java.util.HexFormat;

/** Dependency-free executable contract check against the Python golden vector. */
public final class TelemetryV1 {
    private TelemetryV1() {}

    public static void main(String[] args) {
        String vector = "44540101000000170000000c000102030405060708090a0b0c0d0e0f"
                + "00000000000000070000019e70448800020002"
                + "000102000000000000020109"
                + "0002060000000032000101";
        byte[] bytes = HexFormat.of().parseHex(vector);
        TelemetryFrame frame = TelemetryFrame.decode(bytes);
        if (frame.configRevision() != 12 || frame.sequence() != 7
                || frame.points().size() != 2
                || frame.points().get(0).pointCode() != 1
                || !frame.points().get(0).value().equals((short) 265)
                || !frame.points().get(1).value().equals(true)
                || frame.points().get(1).sampledAt(frame.sampleTimeMs()) != 1780000000050L) {
            throw new AssertionError("golden vector mismatch");
        }

        byte[] truncated = HexFormat.of().parseHex(vector.substring(0, vector.length() - 2));
        expectRejection(truncated);
        byte[] invalidBoolean = bytes.clone();
        invalidBoolean[invalidBoolean.length - 1] = 2;
        expectRejection(invalidBoolean);
        byte[] duplicatePoint = bytes.clone();
        duplicatePoint[59] = 0;
        duplicatePoint[60] = 1;
        expectRejection(duplicatePoint);
        System.out.println("Telemetry v1 Java golden vector and rejection checks OK");
    }

    private static void expectRejection(byte[] data) {
        try {
            TelemetryFrame.decode(data);
            throw new AssertionError("invalid frame accepted");
        } catch (IllegalArgumentException expected) {
            // Rejection is the expected contract behavior.
        }
    }
}
