// UI hint only: the backend revalidates the full current message and permissions.
export function isDirectLaunch(content: string, attachmentCount = 0, toolResult = "") {
  if (attachmentCount || toolResult) return false;
  return /^(?:(?:alt(?:-ai)?|chat)[ ,:]+)?(?:(?:por favor)[ ,]+)?(?:abra|abre|abrir|inicie|inicia)(?:\s+(?:o|a|um|uma))?\s+(?:bloco de notas|bloco notas|notepad|calculadora|calculator)(?:[ ,]+por favor)?[.!?]*$/i.test(content.normalize("NFKC").trim().replace(/\s+/g, " "));
}
