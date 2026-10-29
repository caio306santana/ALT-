# Banco local

O esquema é criado por backend/memory/store.py e pelos serviços de features. Bancos reais ficam em appData e não são versionados.

Tabelas: conversations, messages, settings, audit; memories; scopes, actions, action_context; themes; cloud_usage. Alterações 0.2 adicionam tabelas sem excluir histórico 0.1. Mensagens streaming e propostas em aberto são recuperadas como interrompidas ao reiniciar.

Não fazer downgrade de banco sem backup. Implementar migrações versionadas/backup automático antes de mudanças incompatíveis. Nunca incluir credenciais no histórico; API key fica em arquivo DPAPI separado. Excluir via interface não garante apagamento forense de WAL/backups.
