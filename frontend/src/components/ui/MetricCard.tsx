interface MetricCardProps {
  label: string;
  value: number;
  detail: string;
}

export function MetricCard({ label, value, detail }: MetricCardProps) {
  return (
    <article className="panel rounded p-4">
      <p className="eyebrow">{label}</p>
      <p className="mt-3 font-mono text-3xl font-semibold text-term-text">{value}</p>
      <p className="mt-2 text-sm text-term-muted">{detail}</p>
    </article>
  );
}
