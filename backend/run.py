import json
import os
import socket
import sys
import threading
import psutil
from pathlib import Path
import uvicorn
from backend.api import create_app

def main():
    token = os.environ.get('ALT_SESSION_TOKEN','')
    data_dir = Path(os.environ['ALT_DATA_DIR'])
    app = create_app(data_dir,token)
    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    sock.bind(('127.0.0.1',0)); sock.listen(128)
    print('ALT_READY:'+json.dumps({'port':sock.getsockname()[1]}),flush=True)
    server=uvicorn.Server(uvicorn.Config(app,log_level='warning',access_log=False,timeout_graceful_shutdown=3))
    parent_pid=os.environ.get('ALT_PARENT_PID')
    if parent_pid:
        def watch_parent():
            try: psutil.Process(int(parent_pid)).wait()
            except (psutil.NoSuchProcess,ValueError): pass
            server.should_exit=True
        threading.Thread(target=watch_parent,daemon=True).start()
    server.run(sockets=[sock])

if __name__=='__main__':
    # PyInstaller --noconsole has no stdout; this binary intentionally uses console pipes.
    main()
