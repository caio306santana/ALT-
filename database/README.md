# Banco local

O esquema é criado por backend/memory/store.py e pelos serviços de features. Bancos reais ficam em appData e não são versionados.

Tabelas: conversations, messages, settings, audit; memories; scopes, actions, action_context, tool_authorization; themes; cloud_usage; programs, evaluations e memory_sources. Alterações 0.2/0.3 adicionam tabelas sem excluir histórico anterior. owner_policy fica em settings. Mensagens streaming, propostas e avaliações em aberto são recuperadas como interrompidas ao reiniciar. Jobs e snapshots de navegador são efêmeros e não persistem sessão de site.

Não fazer downgrade de banco sem backup. Implementar migrações versionadas/backup automático antes de mudanças incompatíveis. Nunca incluir credenciais no histórico; API key fica em arquivo DPAPI separado. Excluir via interface não garante apagamento forense de WAL/backups.
