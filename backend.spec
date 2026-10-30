# Backend bundled with its own Python runtime for the Windows installer.
from PyInstaller.utils.hooks import collect_submodules,collect_data_files,collect_dynamic_libs
a = Analysis(['backend/run.py'],pathex=['.'],binaries=collect_dynamic_libs('ctranslate2')+collect_dynamic_libs('pypdfium2_raw'),datas=collect_data_files('faster_whisper')+[('backend/ocr.ps1','backend')],hiddenimports=collect_submodules('uvicorn'),hookspath=[],hooksconfig={},runtime_hooks=[],excludes=[],noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz,a.scripts,[],exclude_binaries=True,name='alt-backend',debug=False,bootloader_ignore_signals=False,strip=False,upx=False,console=True)
coll = COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='alt-backend')
