"""Typing without the read->target chain, and never over an owner's existing text."""
import pytest
from backend.tools.windows_ui import WindowsUI
from backend.tools.direct import direct_action
from test_features import fixture_client
from test_backend import conversation, events


class Value:
    def __init__(self, text, readonly=False): self.CurrentValue = text; self.CurrentIsReadOnly = readonly
    def SetValue(self, text): self.CurrentValue = text


class Element:
    def __init__(self, focus=False): self.CurrentIsPassword = False; self.CurrentHasKeyboardFocus = focus


class Control:
    def __init__(self, kind, text='', name='', focus=False):
        self.iface_value = Value(text); self.kind = kind; self.name = name
        self.element_info = type('Info', (), {'name': name, 'automation_id': '', 'control_type': kind, 'runtime_id': [1], '_element': Element(focus)})()
    def is_visible(self): return True
    def is_enabled(self): return True


class Window:
    def __init__(self, *controls): self.controls = controls
    def descendants(self, depth=5): return list(self.controls)
    def window_text(self): return 'Sem título - Bloco de Notas'


def ui_with(window):
    ui = WindowsUI.__new__(WindowsUI)
    import threading
    ui.lock = threading.RLock(); ui.snapshots = {}
    ui.window = lambda gid: window
    return ui


def test_an_empty_document_receives_the_text():
    doc = Control('Document')
    result = ui_with(Window(Control('Edit', name='Pesquisar'), doc)).type_text('g', 'olá mundo')
    assert doc.iface_value.CurrentValue == 'olá mundo' and result['typed'] and not result['appended']


def test_a_document_with_text_is_never_overwritten():
    doc = Control('Document', 'minha nota não salva')
    with pytest.raises(ValueError, match='já tem texto'):
        ui_with(Window(doc)).type_text('g', 'olá mundo')
    assert doc.iface_value.CurrentValue == 'minha nota não salva'


def test_appending_keeps_the_existing_text():
    doc = Control('Document', 'minha nota')
    result = ui_with(Window(doc)).type_text('g', 'olá mundo', append=True)
    assert doc.iface_value.CurrentValue == 'minha nota\nolá mundo' and result['appended']


def test_without_an_editor_the_focused_text_box_is_used():
    box, focused = Control('Edit', 'antigo', 'Nome'), Control('Edit', '', 'Busca', focus=True)
    ui_with(Window(box, focused)).type_text('g', 'lofi')
    assert focused.iface_value.CurrentValue == 'lofi' and box.iface_value.CurrentValue == 'antigo'


def test_open_and_type_is_a_direct_request():
    action = direct_action('abre o bloco de notas e digita olá mundo')
    assert action.tool == 'windows_type' and action.app == 'notepad' and action.content == 'olá mundo'
    assert direct_action('abra o bloco de notas e escreve "lista de compras"').content == 'lista de compras'


def test_direct_open_and_type_runs_through_the_tool_service(tmp_path):
    app, local, _, client = fixture_client(tmp_path)
    calls = []
    with client:
        scope = client.get('/permissions').json()['scopes'][0]['id']
        client.post('/permissions/grant', json={'level': 4, 'scope_ids': [scope]})
        tools = app.state.tools
        tools.open_and_type = lambda body, fingerprint, event: calls.append(body.content) or {'status': 'done', 'typed': True}
        data = events(client.post('/chat', json={'conversation_id': conversation(client), 'model': 'fixture:4b', 'content': 'abre o bloco de notas e digita olá mundo'}))
        assert next(e for e in data if e['type'] == 'start')['execution'] == 'direct'
        assert calls == ['olá mundo']
        assert 'texto digitado: "olá mundo"' in ''.join(e.get('text', '') for e in data if e['type'] == 'delta')


def test_open_and_write_is_direct_but_other_requests_stay_with_the_model():
    # Before 0.5.6 "abra o bloco de notas e escreva oi" went to the model; it is now one direct action.
    assert direct_action('abra o bloco de notas e escreva oi').content == 'oi'
    assert direct_action('abra o bloco de notas e me explique como usar') is None
