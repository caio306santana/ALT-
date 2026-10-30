import type { Metrics } from "../../../../packages/shared-types";

export function PerformanceDetails({ metrics }: { metrics: Metrics }) {
  const seconds = (value: number | null | undefined) =>
    value == null ? "Não informado" : `${value.toFixed(3)} s`;
  return (
    <details className="performance-details">
      <summary>Desempenho</summary>
      <dl>
        <dt>Primeiro texto desde o envio</dt><dd>{seconds(metrics.request_first_token_seconds)}</dd>
        <dt>Preparação do pedido</dt><dd>{seconds(metrics.preparation_seconds)}</dd>
        <dt>Carregamento do modelo</dt><dd>{seconds(metrics.model_load_seconds)}</dd>
        <dt>Leitura do contexto</dt><dd>{seconds(metrics.prompt_eval_seconds)}</dd>
        <dt>Geração da resposta</dt><dd>{seconds(metrics.generation_seconds)}</dd>
        <dt>Total desde o envio</dt><dd>{seconds(metrics.request_total_seconds)}</dd>
        <dt>Ferramentas oferecidas</dt><dd>{metrics.tools_offered ?? "Não informado"}</dd>
      </dl>
      <small>Tempos medidos no servidor local. Rede e renderização não estão incluídas. Etapas do provedor podem se sobrepor ao primeiro texto.</small>
    </details>
  );
}
