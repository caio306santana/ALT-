"""Which running programs and windows match a name, bringing one to the front, and checking that a
program really opened or closed. Ideas from Mark LVI (core/appidentity.py, actions/open_app.py)."""
import os
import time
from pathlib import Path
from backend.tools.app_catalog import normalize

# Never a target of close_app or "already running": the ALT itself and the model server.
PROTECTED={'ollama.exe','ollama app.exe','llama-server.exe','alt-ai.exe','alt-backend.exe','explorer.exe','dwm.exe','csrss.exe','winlogon.exe','svchost.exe','system'}
MIN_PARTIAL=4

def own_pids():
    """This backend, its parents (Electron) and children, and the desktop app that started it."""
    import psutil
    pids={os.getpid()}
    try:
        me=psutil.Process()
        pids|={p.pid for p in me.parents()}|{p.pid for p in me.children(recursive=True)}
        parent=int(os.environ.get('ALT_PARENT_PID','0') or 0)
        if parent:pids|={parent}|{p.pid for p in psutil.Process(parent).children(recursive=True)}
    except (psutil.Error,ValueError):pass
    return pids

def windows():
    """Visible top-level windows with a title: [(hwnd, pid, title)]."""
    if os.name!='nt':return []
    import ctypes
    from ctypes import wintypes
    user32=ctypes.WinDLL('user32',use_last_error=True);found=[]
    callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    user32.EnumWindows.argtypes=[callback_type,wintypes.LPARAM]
    user32.IsWindowVisible.argtypes=[wintypes.HWND];user32.IsWindowVisible.restype=wintypes.BOOL
    user32.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
    user32.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    @callback_type
    def visit(hwnd,_):
        if user32.IsWindowVisible(hwnd):
            title=ctypes.create_unicode_buffer(256);user32.GetWindowTextW(hwnd,title,256)
            if title.value:
                owner=wintypes.DWORD();user32.GetWindowThreadProcessId(hwnd,ctypes.byref(owner))
                found.append((int(hwnd),owner.value,title.value))
        return True
    user32.EnumWindows(visit,0)
    return found

def exe_name(pid):
    import psutil
    try:return psutil.Process(pid).name()
    except psutil.Error:return ''

def score(words,stem,title):
    """Exact program name 100, prefix 60, contains 30, title only 20 (Mark LVI's ranking).
    Partial matches need at least 4 letters: 'wp' once matched WPS Office."""
    query=' '.join(words);stem=normalize(stem)
    if not query:return 0
    if stem==query or stem.replace(' ','')==query.replace(' ',''):return 100
    if len(query)>=MIN_PARTIAL and stem.startswith(query):return 60
    if len(query)>=MIN_PARTIAL and query in stem:return 30
    if words and set(words)<=set(normalize(title).split()):return 20
    return 0

def matches(name,listing=None,names=exe_name,protected=None):
    """Running programs that match the name, best first: [{'stem','pids','score','windows'}]."""
    words=normalize(name).split();protected=own_pids() if protected is None else protected
    groups={}
    for hwnd,pid,title in (windows() if listing is None else listing):
        exe=names(pid)
        if not exe or pid in protected or exe.casefold() in PROTECTED:continue
        from backend.tools.windows_ui import EXCLUDED
        if exe.casefold() in EXCLUDED:continue
        value=score(words,exe.rsplit('.',1)[0],title)
        if not value:continue
        group=groups.setdefault(exe.casefold(),{'stem':exe.rsplit('.',1)[0],'pids':set(),'score':0,'windows':[]})
        group['pids'].add(pid);group['windows'].append((hwnd,title));group['score']=max(group['score'],value+5)
    return sorted(groups.values(),key=lambda g:-g['score'])

def focus(hwnd):
    """Restore and bring a window to the front. Windows refuses SetForegroundWindow to background
    processes, so borrow the foreground thread's input queue for the call (AttachThreadInput)."""
    if os.name!='nt':return False
    import ctypes
    from ctypes import wintypes
    user32=ctypes.WinDLL('user32',use_last_error=True);kernel32=ctypes.WinDLL('kernel32')
    user32.GetForegroundWindow.restype=wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)];user32.GetWindowThreadProcessId.restype=wintypes.DWORD
    user32.AttachThreadInput.argtypes=[wintypes.DWORD,wintypes.DWORD,wintypes.BOOL]
    user32.ShowWindow.argtypes=[wintypes.HWND,ctypes.c_int];user32.IsIconic.argtypes=[wintypes.HWND]
    user32.SetForegroundWindow.argtypes=[wintypes.HWND];user32.BringWindowToTop.argtypes=[wintypes.HWND]
    user32.GetAncestor.argtypes=[wintypes.HWND,ctypes.c_uint];user32.GetAncestor.restype=wintypes.HWND
    if user32.IsIconic(hwnd):user32.ShowWindow(hwnd,9)  # SW_RESTORE
    if not user32.SetForegroundWindow(hwnd):
        front=user32.GetForegroundWindow()
        other=user32.GetWindowThreadProcessId(front,None);mine=kernel32.GetCurrentThreadId()
        if other and other!=mine:
            user32.AttachThreadInput(mine,other,True)
            try:user32.BringWindowToTop(hwnd);user32.SetForegroundWindow(hwnd)
            finally:user32.AttachThreadInput(mine,other,False)
    front=user32.GetForegroundWindow()
    return bool(front) and (front==hwnd or user32.GetAncestor(front,2)==hwnd)

def link_target(path):
    """Executable behind a Start Menu shortcut, or '' (e.g. a shortcut to a URL)."""
    try:
        import pythoncom,win32com.client
        pythoncom.CoInitialize()
        return win32com.client.Dispatch('WScript.Shell').CreateShortcut(str(path)).TargetPath or ''
    except Exception:return ''

def wait_for_new(before,predicate,timeout=12,interval=.25):
    """First new process (not in `before`) that satisfies the predicate within the timeout."""
    import psutil
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        for proc in psutil.process_iter(['pid','name']):
            if proc.info['pid'] not in before and predicate(proc.info['name'] or ''):return proc.info['pid']
        time.sleep(interval)
    return None

def wait_closed(pids,timeout=6,interval=.15):
    import psutil
    deadline=time.monotonic()+timeout;alive=set(pids)
    while alive and time.monotonic()<deadline:
        alive={pid for pid in alive if psutil.pid_exists(pid)};time.sleep(interval)
    return alive

def post_close(hwnds):
    """WM_CLOSE only: the program may ask to save; nothing is ever killed."""
    import ctypes
    from ctypes import wintypes
    user32=ctypes.WinDLL('user32',use_last_error=True)
    user32.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
    return [h for h in hwnds if user32.PostMessageW(h,0x0010,0,0)]

def stem_of(path):return Path(path).stem.casefold() if path else ''
