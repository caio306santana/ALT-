# Voz local da ALT (0.5)

Tudo roda neste PC: o áudio fica só na memória e nada vai para a internet. Os modelos só são baixados quando o usuário pede, no painel Voz.

| Parte | Arquivo | Como funciona |
| --- | --- | --- |
| Ouvir | `transcriber.py` | faster-whisper small int8 no processador (metade dos núcleos), beam 5, nomes de programas como dica de vocabulário, aquecido ao abrir, clipes com menos de 0,25 s descartados. |
| Captura | `loop.py` | `sounddevice` a 16 kHz. Ctrl+Espaço (configurável) de qualquer lugar do Windows (`GetAsyncKeyState` a 30 Hz, 60 ms de debounce). VAD com piso adaptativo: 700 ms de silêncio terminam a fala. O microfone é ignorado enquanto a ALT fala. |
| Ativação | `wake.py` | "Hey Jarvis" com os modelos ONNX do openWakeWord (CC BY-NC-SA, uso pessoal) direto no onnxruntime. Dorme depois de 2 min sem fala; enquanto dorme, nada vai ao Whisper. "Ei ALT" é experimental: cada fala curta passa pelo Whisper. |
| Falar | `speech.py` | Kokoro ONNX int8, voz `pf_dora` (pt-BR, cerca de 115 MB, cerca de 3x o tempo real na CPU), com a voz do Windows de reserva. Sintetiza a próxima frase enquanto toca a atual. Saída em blocos de 50 ms, para o corte ser instantâneo. |
| Texto falado | `text.py` | Tira `<think>` (mesmo com a tag partida entre trechos), código, links, markdown e emoji. Corta em frases sem quebrar "3.14". |

Medido neste PC:
- a fala da Dora foi transcrita certinho pelo Whisper;
- "Hey Jarvis" sintético deu 0,999 e uma frase comum deu 0,0;
- o primeiro áudio da Dora saiu em 2,2 s com o modelo frio.

Ainda falta validar com um microfone real: o único dispositivo do Windows aqui é o WO Mic, que precisa do app conectado.
