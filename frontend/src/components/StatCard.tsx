interface StatCardProps {
  href?: string;
  label: string;
  value: string | number;
  caption: string;
  tone?: "blue" | "violet" | "amber" | "red";
}

export default function StatCard({ label, value, caption, tone = "blue", href }: StatCardProps) {
  return (
    <article className={`stat-card tone-${tone}`}>
      <span>{href ? <a href={href}>{label} →</a> : label}</span>
      <strong>{value}</strong>
      <p>{caption}</p>
    </article>
  );
}

