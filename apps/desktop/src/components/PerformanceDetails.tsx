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
        {metrics.route && <><dt>Escolha automática</dt><dd>{metrics.route.band} · {metrics.route.reason}</dd></>}
        <dt>Ferramentas oferecidas</dt><dd>{metrics.tools_offered ?? "Não informado"}</dd>
        {metrics.speed && <><dt>Velocidade normal deste PC</dt><dd>{metrics.speed.reference.toFixed(0)} tokens/s ({Math.round(metrics.speed.ratio * 100)}% nesta resposta)</dd></>}
      </dl>
      {metrics.speed?.warning && <p className="performance-warning">{metrics.speed.warning}</p>}
      <small>Tempos medidos no servidor local. Rede e renderização não estão incluídas. Etapas do provedor podem se sobrepor ao primeiro texto.</small>
    </details>
  );
}
