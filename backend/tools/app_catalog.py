"""Installed programs from the Start Menu, opened by name in full access (no manual registration)."""
import difflib
import json
import os
import re
import subprocess
import threading
import time
import unicodedata
from pathlib import Path

SKIP=re.compile(r'(?i)\b(uninstall|desinstal|remover|readme|leia-me|leiame|help|ajuda|manual|website|site oficial|release notes|license|licen[cç]a)\b')
APPID=re.compile(r'^[^"\x00-\x1f]{1,300}$')
# Common spoken names that differ from the Start Menu entry.
ALIASES={'chrome':'google chrome','google':'google chrome','navegador':'google chrome','edge':'microsoft edge',
         'explorador':'explorador de arquivos','explorer':'explorador de arquivos','arquivos':'explorador de arquivos',
         'file explorer':'explorador de arquivos','configuracoes':'configuracoes','settings':'configuracoes',
         'word':'word','excel':'excel','powerpoint':'powerpoint','vscode':'visual studio code','vs code':'visual studio code',
         'code':'visual studio code','zap':'whatsapp','whats':'whatsapp','store':'microsoft store','loja':'microsoft store'}
BROWSERS={'chromehtml':'Google Chrome','msedgehtm':'Microsoft Edge','bravehtml':'Brave','operastable':'Opera','operagxstable':'Opera GX','vivaldihtm':'Vivaldi'}

def normalize(text):
    text=unicodedata.normalize('NFKD',text or '').encode('ascii','ignore').decode().casefold()
    return re.sub(r'[^a-z0-9]+',' ',text).strip()

def default_browser():
    if os.name!='nt':return ''
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice') as key:
            progid=winreg.QueryValueEx(key,'ProgId')[0]
    except OSError:return ''
    lowered=progid.casefold()
    if lowered.startswith('firefoxurl'):return 'Mozilla Firefox'
    return BROWSERS.get(lowered,progid)

class AppCatalog:
    def __init__(self,roots=None,start_apps=True,ttl=600):
        self.roots=roots;self.start_apps=start_apps;self.ttl=ttl
        self.cache=None;self.loaded=0;self.lock=threading.Lock()

    def menu_roots(self):
        if self.roots is not None:return [Path(r) for r in self.roots]
        relative=Path('Microsoft/Windows/Start Menu/Programs')
        return [Path(os.environ[var])/relative for var in ('ProgramData','APPDATA') if os.environ.get(var)]

    def scan(self):
        entries={}
        for root in self.menu_roots():
            if not root.is_dir():continue
            for link in root.rglob('*.lnk'):
                name=link.stem
                if SKIP.search(name):continue
                entries.setdefault(normalize(name),{'name':name,'kind':'lnk','target':str(link)})
        if self.start_apps and os.name=='nt':
            try:
                output=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command','[Console]::OutputEncoding=[Text.Encoding]::UTF8;Get-StartApps | ConvertTo-Json -Compress'],
                    capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=20,creationflags=subprocess.CREATE_NO_WINDOW).stdout
                rows=json.loads(output or '[]')
                for row in rows if isinstance(rows,list) else [rows]:
                    name,appid=str(row.get('Name','')),str(row.get('AppID',''))
                    if not name or not APPID.match(appid) or SKIP.search(name):continue
                    entries.setdefault(normalize(name),{'name':name,'kind':'appx','target':appid})
            except (OSError,ValueError,subprocess.SubprocessError):pass
        return entries

    def entries(self):
        with self.lock:
            if self.cache is None or time.monotonic()-self.loaded>self.ttl:
                self.cache=self.scan();self.loaded=time.monotonic()
            return self.cache

    def names(self):return sorted(entry['name'] for entry in self.entries().values())

    def cached_names(self):
        """Names already scanned; never blocks a chat turn on the 4 s Start Menu scan."""
        cache=self.cache
        return sorted(entry['name'] for entry in cache.values()) if cache else []

    def prewarm(self):threading.Thread(target=self.entries,daemon=True).start()

    def resolve(self,name):
        entries=self.entries();query=normalize(name)
        if not query:raise ValueError('Diga qual aplicativo abrir.')
        query=ALIASES.get(query,query)
        if query in entries:return entries[query]
        # "spotify" -> "Spotify", "chrome" -> "Google Chrome": shortest entry containing every word.
        words=query.split()
        containing=[key for key in entries if all(word in key.split() for word in words)]
        if containing:return entries[min(containing,key=len)]
        prefix=[key for key in entries if key.startswith(query)]
        if prefix:return entries[min(prefix,key=len)]
        close=difflib.get_close_matches(query,list(entries),n=1,cutoff=.75)
        if close:return entries[close[0]]
        suggestions=[entries[key]['name'] for key in difflib.get_close_matches(query,list(entries),n=5,cutoff=.4)]
        raise ValueError(f'Não encontrei "{name}" entre os programas instalados.'+(' Parecidos: '+', '.join(suggestions)+'.' if suggestions else ''))

    def open(self,entry):
        if os.name!='nt':raise ValueError('Aplicativos disponíveis no Windows.')
        if entry['kind']=='lnk':os.startfile(entry['target'])
        else:subprocess.Popen(['explorer.exe','shell:AppsFolder\\'+entry['target']])
        return {'launch_requested':entry['name']}
