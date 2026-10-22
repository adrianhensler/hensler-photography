import argparse
import json
from pathlib import Path

from .catalog import SQLiteCatalog
from .demo import create_demo
from .indexer import load_annotations, scan, separate_paths
from .server import make_server


def main():
    parser = argparse.ArgumentParser(description='Read-only local photo browser')
    commands = parser.add_subparsers(dest='command', required=True)
    demo = commands.add_parser('demo', help='Generate synthetic photos in a new directory')
    demo.add_argument('destination', type=Path)
    for name in ('scan', 'serve'):
        command = commands.add_parser(name)
        command.add_argument('folder', type=Path)
        command.add_argument('--data-dir', type=Path, required=True, help='Separate catalog/cache directory')
        command.add_argument('--metadata', type=Path, help='Optional relative-path JSON annotations')
        if name == 'serve':
            command.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    if args.command == 'demo':
        print(create_demo(args.destination))
        return
    root, data = separate_paths(args.folder, args.data_dir)
    annotations = load_annotations(args.metadata)
    data.mkdir(parents=True, exist_ok=True)
    marker = data / 'root.json'
    if marker.exists() and json.loads(marker.read_text()) != str(root):
        parser.error('This catalog belongs to another folder; use a separate --data-dir')
    catalog = SQLiteCatalog(data / 'catalog.sqlite3')
    marker.write_text(json.dumps(str(root)))
    report = scan(root, data, catalog, annotations)
    print(json.dumps(report, indent=2))
    if args.command == 'serve':
        server = make_server(catalog, data, report, args.port)
        print(f'Open http://127.0.0.1:{server.server_port} — Ctrl+C to stop', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


if __name__ == '__main__':
    main()
