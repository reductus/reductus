import os
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true', help='autoload modules on change')
    parser.add_argument('-x', '--headless', action='store_true', help='do not automatically load client in browser')
    parser.add_argument('--external', action='store_true', help='listen on all interfaces, including external (local connections only if not set)')
    parser.add_argument('-p', '--port', default=8002, type=int, help='port on which to start the server')
    args = parser.parse_args()
    from web_gui.server_flask import app
    if not args.headless:
        import webbrowser
        webbrowser.open("http://localhost:%d" % (args.port))
    host = '0.0.0.0' if args.external else None
    app.run(port=args.port, host=host, debug=args.debug)

if __name__ == '__main__':
    main()
