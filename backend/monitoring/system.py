import platform
import shutil
import psutil

def snapshot(data_dir):
    ram = psutil.virtual_memory()
    disk = shutil.disk_usage(data_dir)
    return {'cpu':{'name':platform.processor() or platform.machine(),'percent':psutil.cpu_percent(),'logical_cores':psutil.cpu_count()},
            'ram':{'total':ram.total,'available':ram.available,'used':ram.used,'percent':ram.percent},
            'disk':{'total':disk.total,'free':disk.free,'used':disk.used},
            'gpu':None,'gpu_temperature':None,'gpu_usage':None,'note':'GPU/VRAM do sistema indisponíveis neste coletor. Alocação dos modelos vem do Ollama /api/ps.'}
