import React from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { BarChart2 } from "lucide-react";
import styles from "./Panels.module.css";
import { useUiStore } from "../state/ui";
import { useParamsStore } from "../state/params";

export const GraphPanel: React.FC = () => {
  const activeWorkspace = useUiStore((s) => s.activeWorkspace);
  const result = useParamsStore((s) => s.results[activeWorkspace]);

  const charts = result?.charts || [];
  const table = result?.table;

  return (
    <div className={styles.graphPanelContent}>
      {charts.length > 0 || table ? (
        <div className={styles.chartsContainer}>
          {charts.map((chart) => {
            const chartData = chart.x.map((xVal, i) => {
              const entry: Record<string, any> = { x: xVal };
              chart.series.forEach((s) => {
                entry[s.name] = s.values[i];
              });
              return entry;
            });

            return (
              <div key={chart.id} className={styles.chartBlock}>
                <div className={styles.chartTitle}>{chart.id.replace(/_/g, " ")}</div>
                <div className={styles.chartWrapper}>
                  <ResponsiveContainer width="100%" height={160}>
                    {chart.kind === "bar" ? (
                      <BarChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                        <CartesianGrid stroke="var(--line)" strokeDasharray="2 2" vertical={false} />
                        <XAxis dataKey="x" stroke="var(--text-3)" tick={{ fill: "var(--text-3)", fontSize: 10 }} />
                        <YAxis stroke="var(--text-3)" tick={{ fill: "var(--text-3)", fontSize: 10 }} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "var(--bg-raised)",
                            borderColor: "var(--line)",
                            borderRadius: "var(--r-pop)",
                            color: "var(--text-1)",
                            fontSize: "11px",
                            fontFamily: "var(--font-mono)",
                          }}
                        />
                        {chart.series.map((s, idx) => (
                          <Bar
                            key={s.name}
                            dataKey={s.name}
                            fill={idx === 0 ? "var(--accent)" : "var(--ok)"}
                            radius={[2, 2, 0, 0]}
                          />
                        ))}
                      </BarChart>
                    ) : (
                      <LineChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                        <CartesianGrid stroke="var(--line)" strokeDasharray="2 2" vertical={false} />
                        <XAxis dataKey="x" stroke="var(--text-3)" tick={{ fill: "var(--text-3)", fontSize: 10 }} />
                        <YAxis stroke="var(--text-3)" tick={{ fill: "var(--text-3)", fontSize: 10 }} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "var(--bg-raised)",
                            borderColor: "var(--line)",
                            borderRadius: "var(--r-pop)",
                            color: "var(--text-1)",
                            fontSize: "11px",
                            fontFamily: "var(--font-mono)",
                          }}
                        />
                        {chart.series.map((s, idx) => (
                          <Line
                            key={s.name}
                            type="monotone"
                            dataKey={s.name}
                            stroke={idx === 0 ? "var(--accent)" : "var(--warn)"}
                            strokeWidth={1.5}
                            dot={chartData.length < 20 ? { r: 2, fill: "var(--accent)" } : false}
                          />
                        ))}
                      </LineChart>
                    )}
                  </ResponsiveContainer>
                </div>
              </div>
            );
          })}

          {table && (
            <div className={styles.tableBlock}>
              <div className={styles.chartTitle}>Summary</div>
              <div className={styles.tableWrapper}>
                <table className={styles.summaryTable}>
                  <thead>
                    <tr>
                      {table.columns.map((col) => (
                        <th key={col}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {table.rows.map((row, rIdx) => (
                      <tr key={rIdx}>
                        {row.map((cell, cIdx) => (
                          <td key={cIdx} className={typeof cell === "number" ? "tabular-nums" : ""}>
                            {typeof cell === "number" ? cell.toFixed(2) : cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className={styles.emptyNotice}>
          <BarChart2 size={20} className={styles.emptyIcon} />
          <span>No Data</span>
        </div>
      )}
    </div>
  );
};
