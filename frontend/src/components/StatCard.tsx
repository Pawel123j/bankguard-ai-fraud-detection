interface StatCardProps {
  label: string;
  value: string | number;
  caption: string;
  tone?: "blue" | "violet" | "amber" | "red";
}

export default function StatCard({ label, value, caption, tone = "blue" }: StatCardProps) {
  return (
    <article className={`stat-card tone-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{caption}</p>
    </article>
  );
}

