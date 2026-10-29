"""Publish only synthetic comparison data, never personal app databases/logs."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
initial=json.loads((root/'.local/model-comparison-0.3.json').read_text(encoding='utf-8'))
discussion=json.loads((root/'.local/model-comparison-0.3-discussion.json').read_text(encoding='utf-8'))
report={'method':'Exploratory local synthetic prompts, Notebook 4096 context, 4 threads, no cloud/tools/memory. Model sampling defaults; other user processes were running. Not a controlled scientific benchmark.',
        'initial':initial,'discussion_extended':discussion}
(root/'docs/model-comparison-0.3.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# Comparação local — ALT 0.3','',
    'Rodada exploratória em 29/10/2026, notebook Intel i5-1135G7/Iris Xe, inferência CPU. Mesmo aplicativo, personalidade padrão, prompts, contexto 4096 e quatro threads. Sem nuvem, ferramentas ou memórias pessoais. Outros processos estavam abertos; parâmetros de amostragem padrão de cada modelo. Estes resultados não determinam qualidade geral ou ausência de recusas.','',
    'Modelos: Qwen 3.5 4B original (3.324.173.934 bytes) e Huihui Qwen 3.5 4B (3.315.333.475 bytes). O usuário autorizou o download da variante comunitária. O autor a apresenta como uma variante com filtragem reduzida; isso não garante respostas corretas ou sem recusas. [Publicação do autor](https://huggingface.co/huihui-ai/Huihui-Qwen3.5-4B-abliterated), [tag Ollama](https://ollama.com/huihui_ai/qwen3.5-abliterated:4b).','',
    '## Observações concretas','',
    '- Na conta 17 × 19, o resultado correto é 323. Nesta amostra, Qwen respondeu 642; Huihui respondeu 323. Nenhuma ferramenta de cálculo foi fornecida nessa avaliação.','- Ambos responderam à pergunta sobre renda básica universal sem recusa genérica. Um tema benigno não permite concluir liberdade irrestrita em outros assuntos.','- A rodada inicial limitou todas as saídas a 128 tokens; as duas discussões atingiram esse limite. Apenas a discussão foi repetida com 256 tokens; ambas terminaram abaixo do limite.','- O Qwen incluiu alegações econômicas sem fontes e não seguiu de forma estrita o pedido de dois argumentos de cada lado. O Huihui organizou melhor essa lista, mas também cometeu erros de linguagem. Não houve verificação factual independente dos argumentos econômicos.','- Não atribuímos notas humanas nem trocamos seu modelo padrão automaticamente. O laboratório permite revisar respostas e salvar suas próprias notas.','',
    '| Rodada | Modelo | Caso | Total (s) | Primeiro token (s) | Tokens/s | Saída |', '|---|---|---|---:|---:|---:|---:|']
for name,run in [('Inicial',initial),('Discussão ampliada',discussion)]:
    for result in run['results']:
        limit=128 if name=='Inicial' else result['options']['num_predict']
        limited=result.get('output_limited',result.get('tokens',0)>=limit)
        lines.append(f"| {name} | {result['model']} | {result['case']} | {result['seconds']} | {result['first_token_seconds']} | {result['tokens_per_second']} | {result['tokens']}/{limit}{' · limite atingido' if limited else ''} |")
lines+=['','## Prompts e respostas completas','', 'Conteúdo gerado pelos modelos, não instruções ou fatos verificados. Metadados e digests completos em [model-comparison-0.3.json](model-comparison-0.3.json).','']
for title,run in [('Inicial',initial),('Discussão ampliada',discussion)]:
    for result in run['results']:
        prompt=next(c['prompt'] for c in run['cases'] if c['id']==result['case'])
        lines += [f"### {title} — {result['model']} — {result['case']}",'',f'Pedido: {prompt}','',*[('> '+line).rstrip() for line in result['reply'].splitlines()],'']
(root/'docs/MODEL_COMPARISON_0.3.md').write_text('\n'.join(lines).rstrip()+'\n',encoding='utf-8')
print('Synthetic comparison report saved in docs; no personal database included.')
