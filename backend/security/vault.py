"""Windows DPAPI user vault. Plaintext API credentials never enter settings/history."""
import ctypes
from ctypes import wintypes
import os
import json
import time
from pathlib import Path

class Blob(ctypes.Structure):
    _fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]

def transform(data,encrypt):
    if os.name!='nt':raise ValueError('Cofre de credenciais disponível apenas no Windows.')
    buffer=ctypes.create_string_buffer(data)
    source=Blob(len(data),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)));result=Blob()
    crypt=ctypes.WinDLL('crypt32',use_last_error=True)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.LocalFree.argtypes=[ctypes.c_void_p];kernel.LocalFree.restype=ctypes.c_void_p
    if encrypt:
        fn=crypt.CryptProtectData;fn.argtypes=[ctypes.POINTER(Blob),wintypes.LPCWSTR,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
        ok=fn(ctypes.byref(source),'ALT-AI',None,None,None,1,ctypes.byref(result))
    else:
        fn=crypt.CryptUnprotectData;fn.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
        ok=fn(ctypes.byref(source),None,None,None,None,1,ctypes.byref(result))
    if not ok:raise ValueError('Falha no cofre DPAPI deste usuário.')
    try:return ctypes.string_at(result.data,result.size)
    finally:kernel.LocalFree(result.data)

class Vault:
    def __init__(self,data_dir):self.path=data_dir/'anthropic-key.dpapi'
    def configured(self):return self.path.exists()
    def save(self,key):
        if not key.startswith('sk-ant-') or len(key)<30 or len(key)>500:raise ValueError('Chave Anthropic inválida.')
        self.path.write_bytes(transform(json.dumps({'key':key.strip(),'validated_at':0,'models':[]}).encode(),True))
    def data(self):
        if not self.configured():return {}
        return json.loads(transform(self.path.read_bytes(),False).decode())
    def get(self):return self.data()['key']
    def validated(self):return bool(self.data().get('validated_at'))
    def model_available(self,model):return model in self.data().get('models',[])
    def validate(self,models):
        data=self.data();data.update(validated_at=time.time() if models else 0,models=models)
        self.path.write_bytes(transform(json.dumps(data).encode(),True))
    def clear(self):self.path.unlink(missing_ok=True)
