"use client";

import { useEffect, useState, type CSSProperties, type FormEvent } from "react";
import { CalendarDays, Check, Pencil, Plus, Target, Trash2, X } from "lucide-react";

import { api, type Goal } from "@/lib/api";

function formatKg(value: string | number) {
  return Number(value).toLocaleString(undefined, {
    maximumFractionDigits: 2,
  });
}

function formatGoalDate(value: string) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString("en-NG", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function GoalProgressRing({ goal }: { goal: Goal }) {
  const progress = Math.max(0, Math.min(Number(goal.progress_percent), 100));
  const goalMet = goal.is_completed;
  const difference = Math.abs(Number(goal.current_co2e) - Number(goal.target_co2e));

  return (
    <div
      className={`goal-ring ${goalMet ? "is-met" : "is-over"}`}
      style={{ "--goal-progress": `${progress}%` } as CSSProperties}
      role="img"
      aria-label={`${goal.name}: ${formatKg(progress)} percent of planned reduction complete. ${goalMet ? "Target met." : `${formatKg(difference)} kilograms over target.`}`}
    >
      <div className="goal-ring-center">
        <strong>{formatKg(progress)}%</strong>
        <span>reduction</span>
      </div>
    </div>
  );
}

function localDateInputValue(date: Date) {
  const year = date.getFullYear().toString().padStart(4, "0");
  const month = (date.getMonth() + 1).toString().padStart(2, "0");
  const day = date.getDate().toString().padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function GoalManager() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<Goal | null>(null);

  useEffect(() => {
    let mounted = true;
    api.goals()
      .then((result) => {
        if (!mounted) return;
        setGoals(result);
      })
      .catch((cause: unknown) => {
        if (mounted) {
          setError(cause instanceof Error ? cause.message : "Goals could not be loaded.");
        }
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  async function saveGoal(payload: GoalFormValues) {
    const nextGoal = editing
      ? await api.updateGoal(editing.id, payload)
      : await api.createGoal(payload);

    setGoals((current) => {
      if (editing) {
        return current.map((item) => (item.id === nextGoal.id ? nextGoal : item));
      }
      return [nextGoal, ...current];
    });
    setEditorOpen(false);
    setEditing(null);
  }

  async function deleteGoal(goal: Goal) {
    if (!window.confirm(`Delete goal “${goal.name}”?`)) return;
    try {
      await api.deleteGoal(goal.id);
      setGoals((current) => current.filter((item) => item.id !== goal.id));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Goal could not be deleted.");
    }
  }

  const hasGoals = goals.length > 0;

  return (
    <div className="goals-page">
      <header className="page-heading goals-heading">
        <div>
          <div className="eyebrow">Progress to target</div>
          <h1>Goals</h1>
          <p>See how your emissions compare with the targets you set.</p>
        </div>
        <button className="button-primary add-activity-button" onClick={() => { setEditing(null); setEditorOpen(true); }}>
          <Plus size={16} /> <span>New goal</span>
        </button>
      </header>

      {error && <div className="form-error activity-error" role="alert">{error}</div>}

      {loading ? (
        <div className="goal-loading" role="status" aria-label="Loading goals">
          {[1, 2, 3].map((item) => <div className="skeleton goal-skeleton" key={item} />)}
        </div>
      ) : hasGoals ? (
        <div className="goal-grid">
          {goals.map((goal) => {
            const difference = Math.abs(Number(goal.current_co2e) - Number(goal.target_co2e));
            return (
            <article className={`panel goal-card ${goal.is_completed ? "goal-card-met" : "goal-card-over"}`} key={goal.id}>
              <div className="goal-card-top">
                <div>
                  <span className="section-kicker">{goal.target_type}</span>
                  <h2>{goal.name}</h2>
                </div>
                <div className={`goal-badge ${goal.is_completed ? "is-complete" : "is-over-target"}`}>
                  {goal.is_completed ? <Check size={14} aria-hidden="true" /> : null}
                  {goal.is_completed ? "Target met" : "Over target"}
                </div>
              </div>

              <div className="goal-card-body">
                <GoalProgressRing goal={goal} />
                <div className="goal-details">
                  <div className="goal-metrics">
                    <div>
                      <span>Current emissions</span>
                      <strong>{formatKg(goal.current_co2e)} <small>kg CO₂e</small></strong>
                    </div>
                    <div>
                      <span>Your target</span>
                      <strong>{formatKg(goal.target_co2e)} <small>kg CO₂e</small></strong>
                    </div>
                    <div>
                      <span>Baseline</span>
                      <strong>{formatKg(goal.baseline_co2e)} <small>kg CO₂e</small></strong>
                    </div>
                  </div>

                  <div className={`goal-result ${goal.is_completed ? "is-met" : "is-over"}`} role="status">
                    {goal.is_completed ? (
                      <>
                        <Check size={16} aria-hidden="true" />
                        <span>
                          {difference === 0
                            ? "You have met your target."
                            : `${formatKg(difference)} kg CO₂e below your target.`}
                        </span>
                      </>
                    ) : (
                      <>
                        <Target size={16} aria-hidden="true" />
                        <span>{formatKg(difference)} kg CO₂e above your target.</span>
                      </>
                    )}
                  </div>

                  <div className="goal-range">
                    <CalendarDays size={15} aria-hidden="true" />
                    <span>{formatGoalDate(goal.start_date)}</span>
                    <span aria-hidden="true">–</span>
                    <span>{formatGoalDate(goal.end_date)}</span>
                  </div>
                </div>
              </div>

              <div className="goal-actions">
                <button className="icon-button" aria-label={`Edit ${goal.name}`} onClick={() => { setEditing(goal); setEditorOpen(true); }}>
                  <Pencil size={15} />
                </button>
                <button className="icon-button danger-button" aria-label={`Delete ${goal.name}`} onClick={() => void deleteGoal(goal)}>
                  <Trash2 size={15} />
                </button>
              </div>
            </article>
            );
          })}
        </div>
      ) : (
        <section className="empty-dashboard panel">
          <div className="empty-emblem"><Target size={27} /></div>
          <span className="section-kicker">A clear target helps</span>
          <h2>No goals yet</h2>
          <p>Create a personal reduction target to see the change you want to make.</p>
          <button className="button-primary" onClick={() => { setEditing(null); setEditorOpen(true); }}><Plus size={16} /> Create a goal</button>
        </section>
      )}

      {editorOpen && <GoalEditor goal={editing} onClose={() => { setEditorOpen(false); setEditing(null); }} onSave={saveGoal} />}
    </div>
  );
}

interface GoalFormValues {
  name: string;
  target_type: string;
  baseline_co2e: string;
  target_co2e: string;
  start_date: string;
  end_date: string;
}

function GoalEditor({
  goal,
  onClose,
  onSave,
}: {
  goal: Goal | null;
  onClose: () => void;
  onSave: (payload: GoalFormValues) => Promise<void>;
}) {
  const [name, setName] = useState(goal?.name ?? "");
  const [targetType, setTargetType] = useState(goal?.target_type ?? "Reduction goal");
  const [baselineCo2e, setBaselineCo2e] = useState(goal?.baseline_co2e ?? "0");
  const [targetCo2e, setTargetCo2e] = useState(goal?.target_co2e ?? "0");
  const [startDate, setStartDate] = useState(goal?.start_date ?? localDateInputValue(new Date()));
  const [endDate, setEndDate] = useState(goal?.end_date ?? localDateInputValue(new Date()));
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await onSave({
        name,
        target_type: targetType,
        baseline_co2e: baselineCo2e,
        target_co2e: targetCo2e,
        start_date: startDate,
        end_date: endDate,
      });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Goal could not be saved.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="activity-editor panel" role="dialog" aria-modal="true" aria-labelledby="goal-editor-title">
        <header className="editor-heading">
          <div>
            <span className="section-kicker">{goal ? "Update target" : "New target"}</span>
            <h2 id="goal-editor-title">{goal ? "Edit goal" : "Create a goal"}</h2>
          </div>
          <button className="icon-button editor-close" aria-label="Close goal form" onClick={onClose}><X size={18} /></button>
        </header>

        <form className="editor-form" onSubmit={submit}>
          <label className="field-label">Goal name
            <input required value={name} onChange={(event) => setName(event.target.value)} maxLength={200} />
          </label>

          <label className="field-label">Target type
            <input value={targetType} onChange={(event) => setTargetType(event.target.value)} maxLength={100} />
          </label>

          <div className="form-grid-two">
            <label className="field-label">Baseline CO₂e (kg)
              <input required type="number" min="0" step="0.01" value={baselineCo2e} onChange={(event) => setBaselineCo2e(event.target.value)} />
            </label>
            <label className="field-label">Target CO₂e (kg)
              <input required type="number" min="0" step="0.01" value={targetCo2e} onChange={(event) => setTargetCo2e(event.target.value)} />
            </label>
          </div>

          <div className="form-grid-two">
            <label className="field-label">Start date
              <input required type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
            </label>
            <label className="field-label">End date
              <input required type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
            </label>
          </div>

          {error && <div className="form-error" role="alert">{error}</div>}

          <div className="editor-actions">
            <button className="button-secondary" type="button" onClick={onClose}>Cancel</button>
            <button className="button-primary" type="submit" disabled={pending}>
              {pending ? "Saving…" : goal ? "Save changes" : "Save goal"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
