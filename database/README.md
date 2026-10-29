# Banco local

O esquema inicial é criado pelo `backend/memory/store.py`. Bancos reais ficam em appData, nunca nesta pasta versionada. Incluir migrações com versão antes de mudanças incompatíveis. Tabelas iniciais: conversations, messages, settings, audit.
