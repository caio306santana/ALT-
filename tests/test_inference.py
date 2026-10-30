from backend.monitoring.inference import inference_metrics
from test_backend import FixtureProvider, client_at, conversation, events, send


def test_provider_nanoseconds_and_unknown_measurements_are_distinguished():
    metrics = inference_metrics({
        'eval_count': 20, 'eval_duration': 2_000_000_000,
        'load_duration': 0, 'prompt_eval_duration': 500_000_000,
        'total_duration': 3_000_000_000,
    }, first=0.75, elapsed=3.2, preparation=0.1, tools_offered=3)
    assert metrics['tokens_per_second'] == 10
    assert metrics['request_first_token_seconds'] == 0.85
    assert metrics['request_total_seconds'] == 3.3
    assert metrics['model_load_seconds'] == 0
    assert metrics['prompt_eval_seconds'] == 0.5
    assert metrics['generation_seconds'] == 2
    assert metrics['provider_total_seconds'] == 3
    unknown = inference_metrics({}, first=None, elapsed=1)
    for key in ('model_load_seconds', 'generation_seconds', 'first_token_seconds', 'tokens_per_second'):
        assert unknown[key] is None


def test_chat_stream_and_saved_history_preserve_performance_details(tmp_path):
    class TimedProvider(FixtureProvider):
        async def stream(self, *args, **kwargs):
            async for chunk in super().stream(*args, **kwargs):
                if chunk.get('done'):
                    chunk.update(load_duration=100_000_000, prompt_eval_duration=200_000_000)
                yield chunk

    with client_at(tmp_path, TimedProvider()) as client:
        cid = conversation(client)
        metrics = events(send(client, cid))[-1]['metrics']
        assert metrics['model_load_seconds'] == 0.1
        assert metrics['prompt_eval_seconds'] == 0.2
        assert metrics['tools_offered'] == 0
        assert metrics['request_first_token_seconds'] >= metrics['first_token_seconds']
        assert client.get(f'/conversations/{cid}/messages').json()[-1]['metrics'] == metrics
