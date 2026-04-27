import type { RiskLevel } from "../api/client";

interface RiskBadgeProps {
  level: RiskLevel;
}

export default function RiskBadge({ level }: RiskBadgeProps) {
  return <span className={`risk-badge risk-${level.toLowerCase()}`}>{level}</span>;
}

