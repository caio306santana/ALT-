"""Conservative profiles; no driver changes or claims about available VRAM."""
import psutil

def performance_profile(requested='auto',game=False):
    ram=psutil.virtual_memory().total
    cores=psutil.cpu_count(logical=False) or 2
    try: portable=psutil.sensors_battery() is not None
    except (AttributeError,OSError): portable=False
    detected='notebook' if portable or ram<20*1024**3 or cores<=4 else 'desktop'
    profile=detected if requested=='auto' else requested
    if game:
        # Game Mode: the model leaves the graphics card and answers on the processor, short and slower.
        options={'num_ctx':4096,'num_predict':512,'num_gpu':0,'num_thread':max(2,min(6,(psutil.cpu_count(logical=False) or 4)-2))}
        return {'requested':requested,'effective':'game','detected':detected,'options':options,'keep_alive':'1m'}
    if profile=='notebook':
        options={'num_ctx':4096,'num_predict':768,'num_thread':max(1,min(4,cores))}
        # Reloading the 4B from disk took 33 s on the notebook (30/10); 15 min covers a pause in the conversation.
        keep_alive='15m'
    else:
        # 1024 tokens is a long answer for a chat; 4096 let old replies ramble for minutes.
        options={'num_ctx':8192,'num_predict':1024}
        # Loaded for 30 min: reloading the 9B took 34-55 s in the 30/10 measurements.
        keep_alive='30m'
    return {'requested':requested,'effective':profile,'detected':detected,'options':options,'keep_alive':keep_alive}
