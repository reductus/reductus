import os
import argparse
import threading
import requests

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true', help='autoload modules on change')
    parser.add_argument('-x', '--headless', action='store_true', help='do not automatically load client in browser')
    parser.add_argument('--external', action='store_true', help='listen on all interfaces, including external (local connections only if not set)')
    parser.add_argument('-p', '--port', default=8002, type=int, help='port on which to start the server')
    parser.add_argument('-c', '--config-file', type=str, help='path to JSON configuration to load')
    parser.add_argument('-i','--instruments', nargs='+', help='instruments to load (overrides config)')
    parser.add_argument('--cache-engine', type=str, default='memory', choices=['memory', 'diskcache', 'redis'], help='select cache engine (default is "memory", overrides config)')
    args = parser.parse_args()
    if args.config_file is not None:
        import json
        config = json.loads(open(args.config_file, 'rt').read())
    else:
        from reductus.dataflow.configure import load_config
        config = load_config(name="config", fallback=True)
    if args.instruments is not None:
        config["instruments"] = args.instruments
    if args.cache_engine is not None:
        config.setdefault("cache", {})
        config["cache"]["engine"] = args.cache_engine
    # Strip "local" from data sources if running external
    if args.external:
        config["data_sources"] = [
            d for d in config["data_sources"]
            if d["name"] != "local"
        ]

    from reductus.web_gui.server_flask import create_app
    app = create_app(config)
    if not args.headless:
        thread = threading.Thread(target=_open_browser_when_server_ready, args=(args.port,))
        thread.start()
    host = '0.0.0.0' if args.external else None
    app.run(port=args.port, host=host, debug=args.debug)

def _open_browser_when_server_ready(port, retry_interval=0.2, max_retries=50):
    # Wait for the server to start
    retry_count = 0
    while retry_count < max_retries:
        try:
            requests.get("http://localhost:%d" % (port), timeout=retry_interval)
            break
        except requests.exceptions.ConnectionError:
            retry_count += 1
    import webbrowser
    webbrowser.open("http://localhost:%d" % (port))

if __name__ == '__main__':
    main()
