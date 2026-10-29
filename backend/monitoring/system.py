import platform
import shutil
import psutil
import json
import subprocess
from functools import lru_cache

@lru_cache(maxsize=1)
def inventory():
    if platform.system()!='Windows': return {'cpu_name':None,'gpu':None}
    # Fixed read-only query. No prompt, URL, path or user argument reaches the shell.
    command="$ErrorActionPreference='Stop'; @{cpu=(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name);gpu=@(Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion)} | ConvertTo-Json -Depth 3 -Compress"
    try:
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
        data=json.loads(result.stdout)
        return {'cpu_name':data.get('cpu'),'gpu':data.get('gpu')}
    except (OSError,ValueError,subprocess.TimeoutExpired): return {'cpu_name':None,'gpu':None}

def snapshot(data_dir):
    hardware=inventory()
    ram = psutil.virtual_memory()
    disk = shutil.disk_usage(data_dir)
    return {'cpu':{'name':hardware['cpu_name'] or platform.processor() or platform.machine(),'percent':psutil.cpu_percent(),'logical_cores':psutil.cpu_count()},
            'ram':{'total':ram.total,'available':ram.available,'used':ram.used,'percent':ram.percent},
            'disk':{'total':disk.total,'free':disk.free,'used':disk.used},
            'gpu':hardware['gpu'],'gpu_temperature':None,'gpu_usage':None,'note':'Uso, temperatura e VRAM total do sistema indisponíveis neste coletor. Alocação dos modelos vem do Ollama /api/ps.'}
