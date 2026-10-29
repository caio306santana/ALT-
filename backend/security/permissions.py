"""Policy is independent from prompts. No operating-system tool exists in this MVP."""
from dataclasses import dataclass, field
import asyncio

@dataclass
class PermissionEngine:
    stopped: bool = False
    active: dict[str, asyncio.Event] = field(default_factory=dict)

    def begin(self, conversation_id: str) -> asyncio.Event:
        if self.stopped:
            raise PermissionError('Ações suspensas. Retome explicitamente para continuar.')
        if conversation_id in self.active:
            raise ValueError('Já existe uma resposta nesta conversa.')
        cancel = asyncio.Event()
        self.active[conversation_id] = cancel
        return cancel

    def stop(self):
        self.stopped = True
        for event in self.active.values():
            event.set()

    def authorize_tool(self, name: str):
        raise PermissionError('Ferramentas do sistema indisponíveis nesta versão. Modo observação.')
