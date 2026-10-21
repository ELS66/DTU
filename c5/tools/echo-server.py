"""Small explicit bench TCP echo server. Never logs payloads or forwards serial data."""
import argparse
import socket
import threading


def serve_client(connection, peer, slots):
    try:
        with connection:
            connection.settimeout(30)
            total = 0
            while True:
                data = connection.recv(4096)
                if not data:
                    break
                connection.sendall(data)
                total += len(data)
            print(f"Closed {peer[0]}:{peer[1]}: {total} bytes echoed", flush=True)
    except (OSError, TimeoutError) as error:
        print(f"Client ended: {type(error).__name__}", flush=True)
    finally:
        slots.release()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", default="127.0.0.1", help="Use this computer's LAN IPv4 for a board test")
    parser.add_argument("--port", type=int, default=9000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be 1..65535")
    slots = threading.BoundedSemaphore(4)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((args.bind, args.port))
        server.listen(4)
        print(f"Bench echo listening on {args.bind}:{args.port}; Ctrl+C stops. Plain TCP, no credentials.", flush=True)
        try:
            while True:
                connection, peer = server.accept()
                if not slots.acquire(blocking=False):
                    connection.close()
                    continue
                threading.Thread(target=serve_client, args=(connection, peer, slots), daemon=True).start()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
