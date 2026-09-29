"""Run a simulated gateway against a local development MQTT broker."""

import argparse
import sys
import time
from pathlib import Path

from mqtt_transport import MqttGateway
from simulator import GatewaySimulator


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("gateway_id")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--username")
    parser.add_argument("--password")
    parser.add_argument("--ca-file", type=Path)
    parser.add_argument("--sample-interval", type=float, default=5.0)
    parser.add_argument("--retry-interval", type=float, default=10.0)
    args = parser.parse_args()
    if args.sample_interval <= 0 or args.retry_interval <= 0:
        parser.error("intervals must be positive")
    try:
        import paho.mqtt.client as mqtt
    except ImportError as exc:
        raise SystemExit("Install MQTT support with: pip install -r dtu-simulator/requirements.txt") from exc
    if args.host not in ("127.0.0.1", "localhost", "::1") and not args.ca_file:
        parser.error("remote brokers require --ca-file for TLS")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                         client_id=f"sim-{args.gateway_id}", protocol=mqtt.MQTTv311)
    if args.username:
        client.username_pw_set(args.username, args.password)
    if args.ca_file:
        client.tls_set(ca_certs=str(args.ca_file))
    adapter = MqttGateway(GatewaySimulator(args.gateway_id), client)
    client.on_connect = adapter.on_connect
    def on_message(client, userdata, message):
        try:
            adapter.on_message(client, userdata, message)
        except (ValueError, UnicodeError) as exc:
            print(f"Ignored invalid MQTT message on {message.topic}: {exc}", file=sys.stderr)

    client.on_message = on_message
    client.connect(args.host, args.port, keepalive=60)
    print(f"Simulated gateway {args.gateway_id} connected; awaiting config/set")
    next_sample = time.monotonic() + args.sample_interval
    next_retry = time.monotonic() + args.retry_interval
    while True:
        client.loop(timeout=1.0)
        now = time.monotonic()
        if now >= next_sample:
            if adapter.gateway.config is not None:
                try:
                    adapter.sample()
                except ValueError as exc:
                    print(f"Sample skipped: {exc}")
            next_sample = now + args.sample_interval
        if now >= next_retry:
            adapter.resend_pending()
            next_retry = now + args.retry_interval


if __name__ == "__main__":
    main()
