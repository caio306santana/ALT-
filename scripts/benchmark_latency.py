"""Synthetic local inference benchmark. Tool calls are recorded, never executed."""
import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.monitoring.inference import inference_metrics
from backend.monitoring.performance import performance_profile
from backend.personality import system_prompt
from backend.providers.ollama import Ollama
from backend.tools.chat_tools import tool_spec


async def main(args):
    ollama = Ollama()
    installed = {m['name'] for m in await ollama.models()
                 if not m.get('remote_host') and not m.get('remote_model') and 'cloud' not in m.get('name', '').lower()}
    missing = set(args.models) - installed
    if missing:
        raise SystemExit('Modelos locais ausentes (nenhum download iniciado): ' + ', '.join(sorted(missing)))
    report = {'created_utc': datetime.now(timezone.utc).isoformat(),
              'scope': 'Inferência local com prompts sintéticos; nenhuma ferramenta executada. Não mede abertura real de programas.',
              'initial_running': await ollama.running(), 'results': []}
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)

    def save():
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    save()
    for model in args.models:
        for case, prompt in [('chat', 'Responda apenas: pronto.'), ('app_proposal', 'Abra o Spotify.')]:
            for repeat in range(args.repeats):
                profile = performance_profile(args.profile)
                profile['options']['num_predict'] = 96
                spec = tool_spec(prompt, {'level': 4}) if case == 'app_proposal' else None
                if spec:
                    profile['tools'] = spec
                messages = [{'role': 'system', 'content': system_prompt({}, tools=bool(spec))},
                            {'role': 'user', 'content': prompt}]
                row = {'model': model, 'case': case, 'repeat': repeat + 1, 'profile': args.profile}
                report['results'].append(row)
                start = time.monotonic()
                first = None
                done = False
                try:
                    async for chunk in ollama.stream(model, messages, asyncio.Event(), profile):
                        message = chunk.get('message', {})
                        if first is None and (message.get('content') or message.get('tool_calls')):
                            first = time.monotonic() - start
                            row['first_output_kind'] = 'tool_call_complete' if message.get('tool_calls') else 'text'
                        if message.get('tool_calls'):
                            row['tool_calls'] = message['tool_calls']
                        if chunk.get('done'):
                            done = True
                            count = len(spec[0]['function']['parameters']['properties']['tool']['enum']) if spec else 0
                            row['metrics'] = inference_metrics(chunk, first=first, elapsed=time.monotonic()-start, tools_offered=count)
                    row['status'] = 'complete' if done else 'incomplete'
                except Exception as exc:
                    row.update(status='error', error=str(exc))
                save()
                print(json.dumps(row, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models', nargs='+', default=['qwen3.5:4b', 'qwen3.5:9b'])
    parser.add_argument('--repeats', type=int, choices=range(1, 6), default=2)
    parser.add_argument('--profile', choices=['auto', 'desktop', 'notebook'], default='desktop')
    parser.add_argument('--output', default='.local/latency-baseline.json')
    asyncio.run(main(parser.parse_args()))
