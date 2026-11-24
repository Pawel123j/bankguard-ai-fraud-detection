import type { Channel, RiskLevel } from "../api/client";

const riskOrder: RiskLevel[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
const channelOrder: Channel[] = ["CARD", "TRANSFER", "ATM", "ONLINE", "BLIK"];

interface ChartProps<T extends string> {
  data: Record<T, number>;
}

function BarChart<T extends string>({ data, order }: ChartProps<T> & { order: T[] }) {
  const max = Math.max(1, ...Object.values<number>(data as Record<string, number>));

  return (
    <div className="bar-chart">
      {order.map((key) => {
        const value = data[key] ?? 0;
        const width = `${Math.max(0, (value / max) * 100)}%`;
        return (
          <div className="chart-row" key={key}>
            <div className="chart-label">
              <span>{key}</span>
              <strong>{value}</strong>
            </div>
            <div className="chart-track">
              <div className={`chart-bar chart-${key.toLowerCase()}`} style={{ width }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function RiskLevelChart({ data }: ChartProps<RiskLevel>) {
  return <BarChart data={data} order={riskOrder} />;
}

export function ChannelChart({ data }: ChartProps<Channel>) {
  return <BarChart data={data} order={channelOrder} />;
}

