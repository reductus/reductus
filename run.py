import os
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--headless', action='store_true', help='do not automatically load client in browser')
    parser.add_argument('-p', '--port', default=8002, type=int, help='port on which to start the server')
    args = parser.parse_args()
    from reflweb.server_flask import app
    if not args.headless:
        import webbrowser
        webbrowser.open("http://localhost:%d" % (args.port))
    app.run(port=args.port)
    
