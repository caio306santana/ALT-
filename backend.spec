# Backend bundled with its own Python runtime for the Windows installer.
from PyInstaller.utils.hooks import collect_submodules
a = Analysis(['backend/run.py'],pathex=['.'],binaries=[],datas=[],hiddenimports=collect_submodules('uvicorn'),hookspath=[],hooksconfig={},runtime_hooks=[],excludes=[],noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz,a.scripts,[],exclude_binaries=True,name='alt-backend',debug=False,bootloader_ignore_signals=False,strip=False,upx=False,console=True)
coll = COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='alt-backend')
