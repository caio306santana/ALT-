"""Several steps in one request, and no "abri"/"baixei" without an action that ran."""
from backend.verification import claimed_action
from test_features import fixture_client
from test_backend import conversation, events


def calls_then(answer, *steps):
    calls = []
    async def model_stream(model, messages, cancel, profile=None):
        calls.append(messages)
        if len(calls) <= len(steps):
            yield {'message': {'tool_calls': [{'function': {'name': 'alt_propose_action', 'arguments': steps[len(calls) - 1]}}]}}
        else:
            yield {'message': {'content': answer}}
        yield {'done': True, 'eval_count': 3}
    return calls, model_stream


def chat(tmp_path, stream, content, level=4, run=None):
    app, local, _, client = fixture_client(tmp_path)
    local.stream = stream
    with client:
        scope = client.get('/permissions').json()['scopes'][0]['id']
        if level: client.post('/permissions/grant', json={'level': level, 'scope_ids': [scope]})
        if run: app.state.tools.run = run
        return events(client.post('/chat', json={'conversation_id': conversation(client), 'model': 'fixture:4b', 'content': content}))


def reply(data): return ''.join(e.get('text', '') for e in data if e['type'] == 'delta')


def test_a_two_step_request_continues_after_the_first_action(tmp_path):
    calls, stream = calls_then('Feito: 4 e 6.', {'tool': 'calculate', 'expression': '2+2'}, {'tool': 'calculate', 'expression': '3+3'})
    data = chat(tmp_path, stream, 'calcule 2+2 e depois calcule 3+3')
    assert len([e for e in data if e['type'] == 'tool_result']) == 2 and len(calls) == 3
    assert 'próxima ação' in calls[1][-1]['content'] and 'Feito: 4 e 6.' in reply(data)


def test_a_single_step_request_does_not_loop_back(tmp_path):
    calls, stream = calls_then('não deveria aparecer', {'tool': 'calculate', 'expression': '2+2'})
    data = chat(tmp_path, stream, 'calcule 2+2')
    assert len(calls) == 1 and len([e for e in data if e['type'] == 'tool_result']) == 1


def test_an_unconfirmed_step_stops_the_sequence(tmp_path):
    calls, stream = calls_then('não deveria aparecer', {'tool': 'calculate', 'expression': '2+2'}, {'tool': 'calculate', 'expression': '3+3'})
    data = chat(tmp_path, stream, 'calcule 2+2 e depois calcule 3+3', run=lambda body, fingerprint, event: {'status': 'unverified', 'notice': 'sem confirmação'})
    assert len(calls) == 1 and 'Parei aqui' in reply(data)


def test_claiming_an_action_that_never_ran_gets_a_warning(tmp_path):
    calls, stream = calls_then('Pronto, abri o Chrome para você.')
    data = chat(tmp_path, stream, 'abre o chrome')
    assert 'Nenhuma ação foi executada nesta resposta' in reply(data)
    assert data[-1]['metrics']['verification']['claimed_without_action'] == 'sem ação'


def test_honest_replies_are_left_alone(tmp_path):
    calls, stream = calls_then('Não abri nada; quer que eu abra o Chrome?')
    data = chat(tmp_path, stream, 'o que você acha do chrome?', level=0)
    assert 'Nenhuma ação' not in reply(data)


def test_claim_detection():
    assert claimed_action('Pronto, já está aberto.') and claimed_action('Baixei o PDF.')
    assert claimed_action('Eu não abri o arquivo.') is None and claimed_action('Posso pesquisar isso.') is None
