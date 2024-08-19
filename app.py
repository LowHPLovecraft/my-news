#!/usr/bin/env python3

import json
import asyncio
import pathlib as pa
import yaml
import traceback

from comms import *
from flask import Flask, send_from_directory, jsonify, request, render_template

reqs = []

app = Flask(__name__, template_folder='public')

config_path = None

@app.route('/favicon.ico')
async def get_ico():
    return send_from_directory('public', 'favicon.ico')

@app.route('/')
async def get_index():
    return render_template('index.html')

@app.route('/public/<path>')
async def get_public(path):
    mimetype = 'application/javascript' if path.endswith('.js') else None
    print(path, mimetype)
    return send_from_directory('public', path, mimetype=mimetype)

@app.route('/status')
async def get_status():
    global reqs
    reqs = yaml.load(pa.Path(config_path).read_text(), Loader=yaml.Loader)
    return dict(reqs=reqs)
    
@app.route('/resource', methods=['POST'])
async def fetch_resource():
    print(request.data)
    data = json.loads(request.data.decode())
    req_type = data.get('type')
    req_args = data.get('args') or {}
    print(req_type, req_args)
    ex = None
    try:
        routine = globals()[req_type]
        res = await routine(**req_args)
    except:
        ex = traceback.format_exc()
        print(ex)
    if ex or not 'items' in res:
        return jsonify(code='error', res=dict(title='', items=[]))
    return jsonify(code='ok', res=res)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-webbrowser', action='store_true')
    parser.add_argument('--port', type=int, default=5004)
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--config', default='data/config.yaml')
    args = parser.parse_args()

    config_path = args.config
    assert config_path

    if not args.no_webbrowser:
        import webbrowser
        webbrowser.open(f'http://localhost:{args.port}/')

    app.run(host='0.0.0.0', port=args.port, debug=args.debug)
