#!/usr/bin/env python3
"""Bundle content.html + templates + fonts into bundle.js so index.html works
when opened directly from disk (file://) with no server.
Run after build.py / policy.py:  python3 bundle.py
"""
import base64, json, pathlib

BASE = pathlib.Path(__file__).parent

def b64(p):
    return base64.b64encode((BASE / p).read_bytes()).decode('ascii')

bundle = {
    'content': b64('content.html'),
    'templates': {
        't1-simple.css': b64('templates/t1-simple.css'),
        't2-rambam.css': b64('templates/t2-rambam.css'),
        't3-gemara.css': b64('templates/t3-gemara.css'),
        't4-parallel.css': b64('templates/t4-parallel.css'),
        't6-anchored.gen.css': b64('templates/t6-anchored.gen.css'),
    },
    'fonts': {
        'noto': b64('fonts/NotoSerifHebrew.woff2'),
        'rubik': b64('fonts/Rubik.woff2'),
    },
}
out = 'window.BUNDLE = ' + json.dumps(bundle) + ';\n'
(BASE / 'bundle.js').write_text(out, encoding='utf-8')
print('wrote bundle.js,', len(out), 'bytes')
