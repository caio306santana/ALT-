"""Conservative profiles; no driver changes or claims about available VRAM."""
import psutil

def performance_profile(requested='auto'):
    ram=psutil.virtual_memory().total
    cores=psutil.cpu_count(logical=False) or 2
    try: portable=psutil.sensors_battery() is not None
    except (AttributeError,OSError): portable=False
    detected='notebook' if portable or ram<20*1024**3 or cores<=4 else 'desktop'
    profile=detected if requested=='auto' else requested
    if profile=='notebook':
        options={'num_ctx':4096,'num_predict':768,'num_thread':max(1,min(4,cores))}
        keep_alive='2m'
    else:
        options={'num_ctx':8192,'num_predict':4096}
        keep_alive='5m'
    return {'requested':requested,'effective':profile,'detected':detected,'options':options,'keep_alive':keep_alive}
