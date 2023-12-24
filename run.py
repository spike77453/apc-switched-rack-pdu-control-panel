import argparse

from apc_switched_rack_pdu_control_panel import app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', help='Host, default is 127.0.0.1', default='127.0.0.1', type=str)
    parser.add_argument('--port', help='Port, default is 5000', default=5000, type=int)
    args = parser.parse_args()

    app.run(host=args.host, port=args.port,  debug=True, use_debugger=False, use_reloader=False)


if __name__ == '__main__':
    main()
