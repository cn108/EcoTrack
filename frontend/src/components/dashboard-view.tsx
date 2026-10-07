"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Activity as ActivityIcon,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  CalendarDays,
  Leaf,
  Plus,
  Sparkles,
  Sprout,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { api, type DashboardData, type MonthlyEmission } from "@/lib/api";

function formatCo2e(value: string | number, digits = 2) {
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function monthRange() {
  const today = new Date();
  const start = new Date(today.getFullYear(), today.getMonth() - 11, 1);
  return {
    start: start.toISOString().slice(0, 10),
    end: today.toISOString().slice(0, 10),
  };
}

function monthLabel(value: string) {
  const [year, month] = value.split("-").map(Number);
  return new Date(year, month - 1, 1).toLocaleDateString(undefined, { month: "short" });
}

export function DashboardView() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [monthly, setMonthly] = useState<MonthlyEmission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    const range = monthRange();
    Promise.all([api.dashboard(), api.monthlyEmissions(range.start, range.end)])
      .then(([summary, emissions]) => {
        if (!mounted) return;
        setDashboard(summary);
        setMonthly(emissions);
      })
      .catch((cause: unknown) => {
        if (mounted) {
          setError(cause instanceof Error ? cause.message : "Dashboard data is unavailable.");
        }
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const isEmpty = Boolean(dashboard && dashboard.activities_this_month === 0 && dashboard.recent_activities.length === 0);
  const change = dashboard?.percentage_change_percent;
  const increase = change !== null && change !== undefined && Number(change) > 0;

  return (
    <div className="dashboard-page">
      <header className="page-heading dashboard-heading">
        <div>
          <div className="eyebrow">Your footprint, in focus</div>
          <h1>Overview</h1>
          <p>See the impact of your everyday choices.</p>
        </div>
        <Link className="button-primary add-activity-button" href="/activities?new=1">
          <Plus size={16} /> <span>Log activity</span>
        </Link>
      </header>

      {loading ? (
        <DashboardLoading />
      ) : error ? (
        <div className="panel error-panel" role="alert">
          <strong>Dashboard unavailable</strong><span>{error}</span>
        </div>
      ) : dashboard ? (
        isEmpty ? (
          <EmptyDashboard />
        ) : (
          <>
            <section className="metrics-grid" aria-label="Monthly summary">
              <article className="metric-card metric-primary">
                <div className="metric-topline"><span>This month</span><span className="metric-icon"><Leaf size={16} /></span></div>
                <div className="metric-value">{formatCo2e(dashboard.current_month_total_co2e)}<small>kg CO₂e</small></div>
                <div className="metric-foot">Total emissions recorded</div>
              </article>
              <article className="metric-card">
                <div className="metric-topline"><span>Monthly change</span><span className={`change-chip ${increase ? "is-up" : "is-down"}`}>
                  {increase ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                  {change === null ? "—" : `${formatCo2e(Math.abs(Number(change)), 1)}%`}
                </span></div>
                <div className="metric-value metric-value-small">{change === null ? "No baseline" : `${increase ? "+" : "−"}${formatCo2e(Math.abs(Number(change)), 1)}%`}</div>
                <div className="metric-foot">Compared with previous month</div>
              </article>
              <article className="metric-card">
                <div className="metric-topline"><span>Daily average</span><span className="metric-icon icon-warm"><CalendarDays size={16} /></span></div>
                <div className="metric-value metric-value-small">{formatCo2e(dashboard.daily_average_co2e)}<small>kg / day</small></div>
                <div className="metric-foot">Based on elapsed days this month</div>
              </article>
              <article className="metric-card">
                <div className="metric-topline"><span>Activities</span><span className="metric-icon icon-blue"><ActivityIcon size={16} /></span></div>
                <div className="metric-value metric-value-small">{dashboard.activities_this_month}<small>logged</small></div>
                <div className="metric-foot">Recorded this month</div>
              </article>
            </section>

            <section className="dashboard-grid dashboard-primary-grid">
              <article className="panel chart-panel">
                <div className="panel-heading">
                  <div><span className="section-kicker">Trend</span><h2>Monthly emissions</h2></div>
                  <span className="panel-period">Last 12 months</span>
                </div>
                <div className="chart-wrap" aria-label="Monthly emissions chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={monthly} margin={{ top: 12, right: 6, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="emissionFill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#4e9674" stopOpacity={0.28} />
                          <stop offset="95%" stopColor="#4e9674" stopOpacity={0.015} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid stroke="#e8ece7" vertical={false} />
                      <XAxis dataKey="month" tickFormatter={monthLabel} tickLine={false} axisLine={false} tick={{ fill: "#366204", fontSize: 11 }} />
                      <YAxis tickLine={false} axisLine={false} tick={{ fill: "#366204", fontSize: 11 }} />
                      <Tooltip
                        formatter={(value) => [`${formatCo2e(String(value))} kg CO₂e`, "Emissions"]}
                        labelFormatter={(label) => monthLabel(String(label))}
                        contentStyle={{ border: "1px solid #e1e7e1", borderRadius: 6, fontSize: 12 }}
                      />
                      <Area type="monotone" dataKey="total_co2e" stroke="#34785c" strokeWidth={2.5} fill="url(#emissionFill)" activeDot={{ r: 4, fill: "#d87358", stroke: "#fff", strokeWidth: 2 }} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </article>

              <article className="panel category-panel">
                <div className="panel-heading">
                  <div><span className="section-kicker">Where it comes from</span><h2>By category</h2></div>
                </div>
                {dashboard.category_totals.length ? (
                  <div className="category-list">
                    {dashboard.category_totals.map((category, index) => {
                      const max = Math.max(...dashboard.category_totals.map((item) => Number(item.total_co2e)), 0.000001);
                      return (
                        <div className="category-item" key={category.category_id}>
                          <div className="category-line"><span className="category-name"><i className={`category-dot dot-${index % 5}`} />{category.category_name}</span><strong>{formatCo2e(category.total_co2e)} <small>kg</small></strong></div>
                          <div className="category-track"><span className={`category-fill fill-${index % 5}`} style={{ width: `${Math.max(3, Number(category.total_co2e) / max * 100)}%` }} /></div>
                        </div>
                      );
                    })}
                  </div>
                ) : <p className="muted-copy">No category data for this month.</p>}
              </article>
            </section>

            <section className="dashboard-grid dashboard-secondary-grid">
              <article className="panel recent-panel">
                <div className="panel-heading">
                  <div><span className="section-kicker">Latest entries</span><h2>Recent activities</h2></div>
                  <Link className="text-link" href="/activities">All activities <ArrowRight size={14} /></Link>
                </div>
                <RecentActivities activities={dashboard.recent_activities} />
              </article>
              <article className="panel highlight-panel">
                <div className="panel-heading"><div><span className="section-kicker">Worth a look</span><h2>Top sources</h2></div><Sparkles size={17} className="highlight-spark" /></div>
                <div className="highlight-item">
                  <span className="highlight-number">01</span>
                  <div><span className="highlight-label">Highest category</span><strong>{dashboard.highest_emission_category?.category_name ?? "—"}</strong></div>
                  {dashboard.highest_emission_category && <span className="highlight-value">{formatCo2e(dashboard.highest_emission_category.total_co2e)} kg</span>}
                </div>
                <div className="highlight-item">
                  <span className="highlight-number">02</span>
                  <div><span className="highlight-label">Activity type</span><strong>{dashboard.highest_emission_activity_type?.activity_type.replaceAll("_", " ") ?? "—"}</strong></div>
                  {dashboard.highest_emission_activity_type && <span className="highlight-value">{formatCo2e(dashboard.highest_emission_activity_type.total_co2e)} kg</span>}
                </div>
                <div className="highlight-tip"><Sprout size={16} /><span>Use your activity history to spot repeat patterns.</span></div>
              </article>
            </section>
          </>
        )
      ) : null}
    </div>
  );
}

function RecentActivities({ activities }: { activities: DashboardData["recent_activities"] }) {
  if (!activities.length) return <p className="muted-copy">No activity recorded yet.</p>;
  return (
    <div className="recent-list">
      {activities.slice(0, 5).map((activity) => (
        <div className="recent-row" key={activity.id}>
          <span className="recent-category-mark"><Leaf size={15} /></span>
          <div className="recent-main"><strong>{activity.activity_type.replaceAll("_", " ")}</strong><span>{activity.category.name} · {activity.activity_date}</span></div>
          <strong className="recent-emission">{formatCo2e(activity.calculated_co2e)} <small>kg</small></strong>
        </div>
      ))}
    </div>
  );
}

function DashboardLoading() {
  return (
    <div className="dashboard-loading" aria-label="Loading dashboard" role="status">
      <div className="metrics-grid">{[1, 2, 3, 4].map((item) => <div className="skeleton metric-skeleton" key={item} />)}</div>
      <div className="dashboard-grid"><div className="skeleton chart-skeleton" /><div className="skeleton category-skeleton" /></div>
      <div className="dashboard-grid"><div className="skeleton category-skeleton" /><div className="skeleton category-skeleton" /></div>
    </div>
  );
}

function EmptyDashboard() {
  return (
    <section className="empty-dashboard panel">
      <div className="empty-emblem"><Leaf size={27} /></div>
      <span className="section-kicker">Your first entry starts here</span>
      <h2>A fresh start, measured.</h2>
      <p>Log an everyday activity to see your footprint take shape. Your CO₂e is calculated securely by EcoTrack using its verified activity factor.</p>
      <Link href="/activities?new=1" className="button-primary"><Plus size={16} /> Log your first activity</Link>
    </section>
  );
}