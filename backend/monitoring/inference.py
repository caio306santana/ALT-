"""Record observed timings; absent provider measurements remain unknown."""


def inference_metrics(chunk, *, first, elapsed, preparation=0, tools_offered=0):
    def seconds(field):
        value = chunk.get(field)
        return round(value / 1e9, 4) if isinstance(value, (int, float)) and value >= 0 else None

    generation = seconds('eval_duration')
    tokens = chunk.get('eval_count')
    return {
        'tokens': tokens,
        'tokens_per_second': round(tokens / generation, 2) if generation and tokens is not None else None,
        'first_token_seconds': round(first, 4) if first is not None else None,
        'request_first_token_seconds': round(preparation + first, 4) if first is not None else None,
        'total_seconds': round(elapsed, 4),
        'request_total_seconds': round(preparation + elapsed, 4),
        'preparation_seconds': round(preparation, 4),
        'model_load_seconds': seconds('load_duration'),
        'prompt_eval_seconds': seconds('prompt_eval_duration'),
        'generation_seconds': generation,
        'provider_total_seconds': seconds('total_duration'),
        'prompt_tokens': chunk.get('prompt_eval_count'),
        'tools_offered': tools_offered,
    }
