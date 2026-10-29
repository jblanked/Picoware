#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Optional loopback AI scene helper. Run --help; Blender needs no pip packages."""
import argparse
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parent
ARTIFACTS = {'scene.glb', 'preview.png', 'preview-middle.png', 'preview-end.png',
             'report.json', 'generated.js', 'request.json', 'history.json'}
SYSTEM = '''You write Three.js ES modules, NOT Blender Python or HTML.
Export function createScene({THREE, seed}) returning {scene, update}.
THREE is supplied (r160). An optional import from "three" resolves to the same bundled version; no other imports. scene must be THREE.Scene.
Use Y up, ordinary Mesh objects with solid MeshStandardMaterial or MeshBasicMaterial.
Use low polygon counts. No textures, vertex colors, skins, instancing, morphs, lines,
points, external assets, network, DOM, cameras, lights, timers or requestAnimationFrame.
For animation, update(t) sets absolute local position/quaternion/scale from time in
seconds. It must support repeated and reverse seeks. Do not accumulate transforms.
All meshes, hierarchy, geometry, materials and visibility stay fixed after creation.
Keep every object visible and the Scene root transform at identity. Use a child
Group for whole-scene movement. Do not add morph targets or morph influences.
Return exactly one fenced javascript code block, containing the complete module.
'''


def write_json(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2), encoding='utf-8')
    temp.replace(path)


def validate_request(data, defaults=None):
    defaults = defaults or {}
    if not isinstance(data, dict):
        raise ValueError('Expected a JSON object')
    result = {}
    result['prompt'] = str(data.get('prompt', '')).strip()
    if not 1 <= len(result['prompt']) <= 12000:
        raise ValueError('Prompt must contain 1–12000 characters')
    result['endpoint'] = str(data.get('endpoint') or defaults.get('endpoint', '')).rstrip('/')
    u = urllib.parse.urlsplit(result['endpoint'])
    if u.scheme not in ('http', 'https') or not u.hostname or u.username or u.password or u.query or u.fragment:
        raise ValueError('Use an http(s) API base URL without embedded credentials, query or fragment')
    result['model'] = str(data.get('model') or defaults.get('model', '')).strip()
    if not result['model'] or len(result['model']) > 250:
        raise ValueError('A model ID is required')
    if not isinstance(data.get('animated', False), bool):
        raise ValueError('animated must be boolean')
    result['animated'] = data.get('animated', False)
    for name, default, low, high in [('triangle_target',1000,12,4096), ('fps',24,1,60), ('seed',1,0,2147483647)]:
        value = data.get(name, default)
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f'{name} must be an integer between {low} and {high}')
        result[name] = value
    duration = data.get('duration', 4.0)
    if type(duration) not in (int, float) or not 0.1 <= duration <= 30:
        raise ValueError('duration must be between 0.1 and 30 seconds')
    if round(duration * result['fps']) < 1:
        raise ValueError('Duration must cover at least one frame')
    result['duration'] = duration
    return result


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Model API redirects are not permitted; configure the final endpoint')


def completion(request, messages):
    payload = {'model': request['model'], 'messages': messages, 'temperature': 0.7,
               'top_p': 0.95, 'max_tokens': 7000, 'stream': False,
               'chat_template_kwargs': {'enable_thinking': False}}
    headers = {'Content-Type': 'application/json'}
    key = os.environ.get('PICOWARE_MODEL_API_KEY')
    if key:
        headers['Authorization'] = 'Bearer ' + key
    req = urllib.request.Request(request['endpoint'] + '/chat/completions',
                                 json.dumps(payload).encode(), headers)
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(req, timeout=120) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError('Model response exceeds 2 MB')
        data = json.loads(raw)
        if data['choices'][0].get('finish_reason') == 'length':
            raise ValueError('Model output was truncated; reduce scene complexity')
        content = data['choices'][0]['message']['content']
        if not isinstance(content, str):
            raise ValueError('Model did not return text')
        return content
    except urllib.error.HTTPError as exc:
        raise ValueError(f'Model API HTTP {exc.code}; check endpoint, model and helper credentials') from None


def extract_code(content):
    blocks = re.findall(r'```(?:javascript|js|mjs)?\s*\n(.*?)```', content, re.S)
    code = blocks[0] if len(blocks) == 1 else content.strip()
    if len(code) > 200_000 or 'createScene' not in code:
        raise ValueError('Return one complete ES module exporting createScene')
    # Normalize only the module interface, never rewrite scene geometry or animation.
    if re.search(r'(?m)^function createScene\s*\(', code) and not re.search(r'\bexport\s+(?:function\s+createScene|\{[^}]*\bcreateScene\b)', code):
        code += '\nexport { createScene };\n'
    return code


def network_sandbox():
    """Fail closed: browser network traffic must be blocked below web APIs."""
    executable = shutil.which('bwrap') if sys.platform == 'linux' else None
    if executable is None:
        raise RuntimeError('Scene validation requires Linux and bubblewrap (bwrap) for network isolation')
    command = [executable, '--unshare-net', '--die-with-parent', '--bind', '/', '/', '--dev', '/dev', '--']
    try:
        probe = subprocess.run(command + ['/bin/true'], capture_output=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError('Cannot establish browser network isolation: ' + str(exc)) from None
    if probe.returncode:
        raise RuntimeError('Cannot establish browser network isolation; enable unprivileged user/network namespaces: ' + probe.stderr.decode(errors='replace')[:500])
    return command


def validate_scene(directory, request, executable=None):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError('Install helper dependencies: pip install -r requirements.txt; python -m playwright install chromium') from None
    files = {'/': ('text/html', '<!doctype html><meta charset="utf-8"><style>body{margin:0}</style><script type="importmap" nonce="picoware-local-importmap">{"imports":{"three":"/vendor/three.module.js"}}</script><script type="module" src="/runner.js"></script>'),
             '/runner.js': ('text/javascript', (ROOT/'runner.js').read_text()),
             '/generated.js': ('text/javascript', (directory/'generated.js').read_text())}
    for name in ('three.module.js', 'GLTFExporter.js', 'TextureUtils.js'):
        files['/vendor/'+name] = ('text/javascript', (ROOT/'vendor'/name).read_text())
    errors = []
    sandbox = network_sandbox()
    with sync_playwright() as pw, tempfile.TemporaryDirectory(prefix='picoware-browser-') as launch_dir:
        # Playwright talks through inherited pipes; the browser needs no network,
        # including loopback. Interception below supplies all bundled resources.
        launcher = Path(launch_dir)/'chromium'
        launcher.write_text('#!/bin/sh\nexec ' + shlex.join(sandbox + [executable or pw.chromium.executable_path]) + ' "$@"\n')
        launcher.chmod(0o700)
        # Browser receives no model/API credentials. Chromium's sandbox stays enabled.
        env = {k:v for k,v in os.environ.items() if k in ('PATH','HOME','DISPLAY','XAUTHORITY','TMPDIR','LANG','XDG_RUNTIME_DIR')}
        try:
            browser = pw.chromium.launch(headless=True, chromium_sandbox=True,
                executable_path=str(launcher), env=env, args=['--enable-unsafe-swiftshader'])
        except Exception as exc:
            raise RuntimeError('Chromium could not start; check browser installation and sandbox support: ' + str(exc)[:500]) from None
        try:
            context = browser.new_context(viewport={'width':800,'height':600},
                                          service_workers='block', accept_downloads=False)
            def route_handler(route):
                u = urllib.parse.urlsplit(route.request.url)
                item = files.get(u.path) if u.scheme == 'http' and u.netloc == 'picoware.invalid' and not u.query else None
                if item is None or route.request.method != 'GET':
                    errors.append('External resource access blocked: '+u.scheme+'://'+u.netloc)
                    route.abort()
                else:
                    route.fulfill(status=200,content_type=item[0],body=item[1],headers={
                        'Content-Security-Policy': "default-src 'none'; script-src 'self' 'nonce-picoware-local-importmap'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; worker-src 'none'; object-src 'none'; base-uri 'none'"})
            context.route('**/*', route_handler)
            context.route_web_socket('**/*', lambda ws: ws.close())
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto('http://picoware.invalid/', wait_until='load', timeout=15000)
            page.wait_for_function('typeof window.runScene === "function"', timeout=15000)
            result = page.evaluate('(options) => window.runScene(options)', {**request, 'job_id':directory.name.replace('-','')[:12]})
            if errors:
                raise ValueError('; '.join(errors)[:2000])
            glb = base64.b64decode(result['glb'], validate=True)
            if len(glb) > 20_000_000 or glb[:4] != b'glTF':
                raise ValueError('Invalid or excessive GLB output')
            (directory/'scene.glb').write_bytes(glb)
            page.screenshot(path=str(directory/'preview.png'))
            result['report']['glb_sha256'] = hashlib.sha256(glb).hexdigest()
            write_json(directory/'report.json',result['report'])
            return result['report']
        finally:
            browser.close()


def check_dependencies(executable=None):
    network_sandbox()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError('Install helper dependencies: pip install -r requirements.txt') from None
    with sync_playwright() as pw:
        path = executable or pw.chromium.executable_path
        if not Path(path).is_file():
            raise RuntimeError('Chromium missing: run python -m playwright install chromium')
    return path


def run_worker(directory, executable=None):
    check_dependencies(executable)
    request = json.loads((directory/'request.json').read_text())
    prompt = (f"{request['prompt']}\nTriangle target {request['triangle_target']}, hard maximum 4096. "
              f"{'Animated' if request['animated'] else 'Static'} output; duration {request['duration']} seconds. "
              'For static output update may be omitted.')
    messages = [{'role':'system','content':SYSTEM}, {'role':'user','content':prompt}]
    history = []
    for attempt in range(3):
        write_json(directory/'progress.json',{'phase':'generating' if not attempt else 'repairing','attempt':attempt+1})
        try:
            content = completion(request,messages)
            (directory/f'response-{attempt+1}.txt').write_text(content)
            messages.append({'role':'assistant','content':content})
            code = extract_code(content)
            (directory/'generated.js').write_text(code)
            (directory/f'attempt-{attempt+1}.js').write_text(code)
            write_json(directory/'progress.json',{'phase':'validating','attempt':attempt+1})
            report = validate_scene(directory,request,executable)
            history.append({'attempt':attempt+1,'result':'passed'})
            write_json(directory/'history.json',history)
            return
        except Exception as exc:
            error = str(exc)[:3000]
            history.append({'attempt':attempt+1,'error':error})
            write_json(directory/'history.json',history)
            # Dependency/API failures cannot be repaired by changing scene code.
            if isinstance(exc, (OSError, RuntimeError, urllib.error.URLError)) or 'Model API HTTP' in error:
                raise
            messages.append({'role':'user','content':'Validation failed: '+error+'\nReturn the complete corrected module. Keep the requested scene.'})
    raise ValueError('Generation failed after the initial attempt and two repairs: '+history[-1]['error'])


class Jobs:
    def __init__(self, root, defaults, executable=None, timeout=420):
        self.root, self.defaults, self.executable, self.timeout = root, defaults, executable, timeout
        self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.lock = threading.RLock()
        self.jobs = {}
        # Persist finished jobs across restarts; never pretend an interrupted job succeeded.
        for path in self.root.glob('*/status.json'):
            try:
                status = json.loads(path.read_text())
                if status['status'] not in ('complete','failed','cancelled'):
                    status.update(status='failed',error='Helper restarted during this job')
                    write_json(path,status)
                self.jobs[path.parent.name]={'status':status,'process':None}
            except (ValueError,KeyError):
                continue

    def submit(self,data):
        request = validate_request(data,self.defaults)
        with self.lock:
            if any(j['status']['status'] in ('queued','running') for j in self.jobs.values()):
                raise BlockingIOError('One generation is already running; cancel it or wait')
            ident = uuid.uuid4().hex
            directory = self.root/ident
            directory.mkdir(mode=0o700)
            write_json(directory/'request.json',request)
            status = {'id':ident,'status':'queued','phase':'queued','attempt':0}
            self.jobs[ident]={'status':status,'process':None}
            write_json(directory/'status.json',status)
            threading.Thread(target=self._run,args=(ident,),daemon=True).start()
            return dict(status)

    @staticmethod
    def stop(process):
        if process and process.poll() is None:
            if os.name == 'posix':
                # Playwright may put Chromium in its own process group. Capture the
                # descendant tree before killing its worker, then reap every child.
                parents = {}
                for entry in Path('/proc').glob('[0-9]*/status'):
                    try:
                        fields = entry.read_text().splitlines()
                        parent = int(next(line.split()[1] for line in fields if line.startswith('PPid:')))
                        parents.setdefault(parent, []).append(int(entry.parent.name))
                    except (OSError,ValueError,StopIteration): pass
                descendants = []
                def collect(pid):
                    for child in parents.get(pid, []):
                        collect(child); descendants.append(child)
                collect(process.pid)
                for pid in descendants:
                    try: os.kill(pid,signal.SIGKILL)
                    except ProcessLookupError: pass
                try: os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError: pass
            else:
                process.kill()

    def _run(self,ident):
        directory = self.root/ident
        with self.lock:
            job = self.jobs[ident]
            if job['status']['status'] == 'cancelled': return
            command = [sys.executable,str(ROOT/'helper.py'),'--worker',str(directory)]
            if self.executable: command += ['--chromium',self.executable]
            log = (directory/'worker.log').open('wb')
            try:
                process = subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
            except OSError as exc:
                log.close();job['status'].update(status='failed',error=str(exc));write_json(directory/'status.json',job['status']);return
            job['process']=process
            job['status'].update(status='running')
            write_json(directory/'status.json',job['status'])
        error = None
        try:
            process.wait(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            error = f'Job exceeded {self.timeout} seconds; reduce complexity or retry'
            self.stop(process);process.wait()
        finally:
            log.close()
        with self.lock:
            if job['status']['status'] == 'cancelled': return
            progress=directory/'progress.json'
            if progress.exists(): job['status'].update(json.loads(progress.read_text()))
            failure=directory/'failure.json'
            if failure.exists(): error=json.loads(failure.read_text()).get('error','Generation failed')
            if process.returncode or error:
                job['status'].update(status='failed',error=error or 'Worker failed; see worker.log')
            else:
                try:
                    report=json.loads((directory/'report.json').read_text())
                    job['status'].update(status='complete',phase='complete',triangles=report['triangles'],tracks=report['tracks'],warnings=report['warnings'])
                except (OSError,ValueError,KeyError):
                    job['status'].update(status='failed',error='Worker produced no valid report')
            write_json(directory/'status.json',job['status'])

    def status(self,ident):
        with self.lock:
            if ident not in self.jobs: raise KeyError(ident)
            status=dict(self.jobs[ident]['status'])
            p=self.root/ident/'progress.json'
            if p.exists() and status['status']=='running':status.update(json.loads(p.read_text()))
            return status

    def cancel(self,ident):
        with self.lock:
            job=self.jobs[ident]
            if job['status']['status'] in ('queued','running'):
                job['status'].update(status='cancelled',phase='cancelled')
                self.stop(job['process'])
                write_json(self.root/ident/'status.json',job['status'])
            return dict(job['status'])

    def shutdown(self):
        for ident in list(self.jobs):self.cancel(ident)


def make_handler(jobs,token):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass  # Never log authorization headers or prompts.
        def send(self,status,value):
            body=json.dumps(value).encode()
            self.send_response(status);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def authorized(self):
            if self.headers.get('Origin') or not hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+token):
                self.send(403,{'error':'Helper token required; browser-origin API calls are forbidden'});return False
            return True
        def do_GET(self):
            if not self.authorized():return
            parts=self.path.strip('/').split('/')
            try:
                if self.path=='/health':
                    try: check_dependencies(jobs.executable); dependency_error=None
                    except RuntimeError as exc: dependency_error=str(exc)
                    return self.send(200,{'api_version':1,'status':'ok','defaults':jobs.defaults,'dependency_error':dependency_error})
                if len(parts)==2 and parts[0]=='jobs':return self.send(200,jobs.status(parts[1]))
                if len(parts)==4 and parts[0]=='jobs' and parts[2]=='artifacts' and parts[3] in ARTIFACTS:
                    status=jobs.status(parts[1])
                    if parts[3] in ('scene.glb','preview.png','preview-middle.png','preview-end.png','report.json') and status['status']!='complete':
                        return self.send(409,{'error':'Job is not complete'})
                    path=jobs.root/parts[1]/parts[3]
                    if not path.is_file():raise KeyError('artifact')
                    body=path.read_bytes();self.send_response(200);self.send_header('Content-Type','application/octet-stream');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);return
                raise KeyError('route')
            except KeyError:self.send(404,{'error':'Job or artifact not found'})
        def do_POST(self):
            if not self.authorized():return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<=length<=20000:raise ValueError('Request too large')
                data=json.loads(self.rfile.read(length) or b'{}')
                parts=self.path.strip('/').split('/')
                if self.path=='/jobs':return self.send(202,jobs.submit(data))
                if len(parts)==3 and parts[0]=='jobs' and parts[2]=='cancel':return self.send(200,jobs.cancel(parts[1]))
                self.send(404,{'error':'Unknown route'})
            except KeyError:self.send(404,{'error':'Job not found'})
            except BlockingIOError as exc:self.send(409,{'error':str(exc)})
            except (ValueError,TypeError) as exc:self.send(400,{'error':str(exc)})
    return Handler


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8766)
    parser.add_argument('--jobs',type=Path,default=Path.home()/'.local/share/picoware-ai/jobs')
    parser.add_argument('--endpoint',default='http://127.0.0.1:11438/v1')
    parser.add_argument('--model',default='qwen3.5-4b-3d-coder-Q8_0')
    parser.add_argument('--chromium',help='Optional installed Chromium executable; default is pinned Playwright Chromium')
    parser.add_argument('--worker',type=Path,help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.worker:
        try:run_worker(args.worker,args.chromium)
        except Exception as exc:
            write_json(args.worker/'failure.json',{'error':str(exc)[:3000]});return 1
        return 0
    token=os.environ.get('PICOWARE_HELPER_TOKEN') or secrets.token_urlsafe(32)
    if len(token)<16:parser.error('PICOWARE_HELPER_TOKEN must contain at least 16 characters')
    jobs=Jobs(args.jobs,{'endpoint':args.endpoint,'model':args.model},args.chromium)
    server=ThreadingHTTPServer(('127.0.0.1',args.port),make_handler(jobs,token))
    print(f'Picoware AI helper: http://127.0.0.1:{args.port}\nHelper token (paste into Blender): {token}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:jobs.shutdown();server.server_close()
    return 0

if __name__=='__main__':sys.exit(main())
