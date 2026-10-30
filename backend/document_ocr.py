"""Render scanned PDF pages and recognize them locally with Windows OCR."""
import json
import math
import os
import subprocess
import tempfile
import threading
from pathlib import Path

_PDFIUM_LOCK = threading.Lock()  # PDFium is not thread-safe.
MAX_OCR_PAGES = 50


def recognize_images(paths):
    if os.name != 'nt':
        raise ValueError('Este PDF precisa de OCR local, disponível no aplicativo Windows.')
    helper = Path(__file__).with_name('ocr.ps1')
    try:
        result = subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-File', str(helper)],
            input=json.dumps({'paths': [str(Path(path).resolve()) for path in paths]}),
            capture_output=True, text=True, encoding='utf-8', timeout=180,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode:
            raise ValueError('Não foi possível usar o OCR local do Windows. Confira o idioma de reconhecimento instalado e tente novamente.')
        rows = json.loads(result.stdout)
        if not isinstance(rows, list) or len(rows) != len(paths):
            raise ValueError('O OCR local não devolveu todas as páginas.')
        return [row['text'] for row in rows]
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError('Falha na leitura por OCR local. Tente um PDF menor ou uma cópia com texto selecionável.') from exc


def pdf_ocr(path, page_indexes):
    if len(page_indexes) > MAX_OCR_PAGES:
        raise ValueError(f'O PDF tem mais de {MAX_OCR_PAGES} páginas que precisam de OCR. Divida-o em arquivos menores; nenhuma página foi omitida.')
    import pypdfium2 as pdfium
    with tempfile.TemporaryDirectory(prefix='alt-pdf-ocr-') as temporary:
        paths = []
        with _PDFIUM_LOCK:
            document = pdfium.PdfDocument(str(path))
            try:
                for index in page_indexes:
                    page = document[index]
                    try:
                        width, height = page.get_size()
                        if not all(math.isfinite(v) and v > 0 for v in (width, height)):
                            raise ValueError('Dimensões inválidas em uma página do PDF.')
                        bitmap = page.render(scale=min(2.5, 2200 / max(width, height)))
                        try:
                            image = bitmap.to_pil()
                            try:
                                target = Path(temporary) / f'page-{index+1}.png'
                                image.save(target)
                                paths.append(target)
                            finally:
                                image.close()
                        finally:
                            bitmap.close()
                    finally:
                        page.close()
            finally:
                document.close()
        return dict(zip(page_indexes, recognize_images(paths)))
