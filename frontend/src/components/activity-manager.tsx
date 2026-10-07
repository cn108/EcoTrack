"use client";

import { useEffect, useState, type FormEvent } from "react";
import { CalendarDays, ChevronLeft, ChevronRight, Pencil, Plus, Search, Trash2, X } from "lucide-react";

import {
  api,
  ApiError,
  type Activity,
  type ActivityOptions,
  type ActivityPayload,
  type CategoryOption,
} from "@/lib/api";

const PAGE_SIZE = 10;

function formatCo2e(value: string) {
  return Number(value).toLocaleString(undefined, {
    maximumFractionDigits: 2,
  });
}

function formatQuantity(value: string) {
  return Number(value).toLocaleString("en-NG", {
    maximumFractionDigits: 2,
  });
}

function formatFactor(value: string) {
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: 3,
    maximumFractionDigits: 6,
  });
}

function formatNaira(value: number) {
  return new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency: "NGN",
    maximumFractionDigits: 2,
  }).format(value);
}

export function ActivityManager({ initialOpen = false }: { initialOpen?: boolean }) {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [options, setOptions] = useState<ActivityOptions | null>(null);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [page, setPage] = useState(0);
  const [reloadCount, setReloadCount] = useState(0);
  const [hasNextPage, setHasNextPage] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editorOpen, setEditorOpen] = useState(initialOpen);
  const [editing, setEditing] = useState<Activity | null>(null);
  const [lastSaved, setLastSaved] = useState<Activity | null>(null);

  useEffect(() => {
    let mounted = true;
    api.activityOptions()
      .then((result) => { if (mounted) setOptions(result); })
      .catch((cause: unknown) => { if (mounted) setError(cause instanceof Error ? cause.message : "Options could not be loaded."); });
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    let mounted = true;
    const query = new URLSearchParams({ skip: String(page * PAGE_SIZE), limit: String(PAGE_SIZE) });
    if (categoryFilter) query.set("category_id", categoryFilter);
    if (typeFilter) query.set("activity_type", typeFilter);
    if (startDate) query.set("start_date", startDate);
    if (endDate) query.set("end_date", endDate);
    api.activities(query)
      .then((result) => {
        if (!mounted) return;
        setActivities(result);
        setHasNextPage(result.length === PAGE_SIZE);
      })
      .catch((cause: unknown) => { if (mounted) setError(cause instanceof Error ? cause.message : "Activities could not be loaded."); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [categoryFilter, endDate, page, reloadCount, startDate, typeFilter]);

  function openCreate() {
    setEditing(null);
    setEditorOpen(true);
  }

  async function deleteActivity(activity: Activity) {
    if (!window.confirm(`Delete “${activity.activity_type.replaceAll("_", " ")}”?`)) return;
    try {
      await api.deleteActivity(activity.id);
      setActivities((current) => current.filter((item) => item.id !== activity.id));
      setLastSaved(null);
      if (activities.length === 1 && page > 0) setPage((current) => current - 1);
      else setReloadCount((current) => current + 1);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Activity could not be deleted.");
    }
  }

  function changeFilter(update: () => void) {
    setLoading(true);
    setError(null);
    update();
    setPage(0);
  }

  function changePage(nextPage: number) {
    setLoading(true);
    setError(null);
    setPage(nextPage);
  }

  const availableTypes = options?.emission_factors
    .filter((factor) => !categoryFilter || factor.category === options.categories.find((category) => category.id === categoryFilter)?.name)
    .map((factor) => factor.activity_type) ?? [];

  return (
    <div className="activities-page">
      <header className="page-heading activities-heading">
        <div>
          <div className="eyebrow">Your record</div>
          <h1>Activities</h1>
          <p>Review your recorded quantities, emissions, and estimated fuel costs.</p>
        </div>
        <button className="button-primary add-activity-button" onClick={openCreate}>
          <Plus size={16} /> <span>Log activity</span>
        </button>
      </header>

      {lastSaved && (
        <div className="saved-result" role="status">
          <span>Calculated by EcoTrack</span>
          <strong>{formatCo2e(lastSaved.calculated_co2e)} kg CO₂e</strong>
          <small>{lastSaved.emission_factor.source_name}</small>
          <button className="icon-button" aria-label="Dismiss result" onClick={() => setLastSaved(null)}><X size={16} /></button>
        </div>
      )}

      <section className="filter-bar panel" aria-label="Filter activities">
        <div className="filter-heading"><Search size={15} /><span>Filter entries</span></div>
        <label className="filter-control">Category
          <select value={categoryFilter} onChange={(event) => changeFilter(() => setCategoryFilter(event.target.value))}>
            <option value="">All categories</option>
            {options?.categories.map((category) => <option value={category.id} key={category.id}>{category.name}</option>)}
          </select>
        </label>
        <label className="filter-control">Activity type
          <select value={typeFilter} onChange={(event) => changeFilter(() => setTypeFilter(event.target.value))}>
            <option value="">All types</option>
            {[...new Set(availableTypes)].sort().map((type) => <option key={type} value={type}>{type.replaceAll("_", " ")}</option>)}
          </select>
        </label>
        <label className="filter-control">From
          <input type="date" value={startDate} onChange={(event) => changeFilter(() => setStartDate(event.target.value))} />
        </label>
        <label className="filter-control">To
          <input type="date" value={endDate} onChange={(event) => changeFilter(() => setEndDate(event.target.value))} />
        </label>
      </section>

      {error && <div className="form-error activity-error" role="alert">{error}</div>}

      <section className="panel activity-table-panel">
        <div className="activity-table-heading">
          <div><span className="section-kicker">Activity log</span><h2>Recorded emissions</h2></div>
          <span className="row-count">{loading ? "Loading…" : `${activities.length} ${activities.length === 1 ? "activity" : "activities"}`}</span>
        </div>
        {loading ? (
          <div className="table-loading" role="status" aria-label="Loading activities">{[1, 2, 3, 4].map((row) => <div className="skeleton table-skeleton" key={row} />)}</div>
        ) : activities.length === 0 ? (
          <div className="table-empty">
            <span className="empty-emblem small-emblem"><CalendarDays size={20} /></span>
            <strong>No activities found</strong>
            <p>Try a different filter or log an activity to begin your record.</p>
            <button className="button-secondary" onClick={openCreate}><Plus size={15} /> Log activity</button>
          </div>
        ) : (
          <div className="table-scroll">
            <table className="activity-table">
              <caption className="sr-only">Recorded activities with quantity, emissions, and estimated fuel spend</caption>
              <thead><tr><th scope="col">Activity</th><th scope="col">Category</th><th scope="col">Quantity</th><th scope="col">Date logged</th><th scope="col">Emissions (kg CO₂e)</th><th scope="col">Estimated spend (NGN)</th><th scope="col"><span className="sr-only">Actions</span></th></tr></thead>
              <tbody>
                {activities.map((activity) => (
                  <tr key={activity.id}>
                    <td>
                      <strong>{activity.activity_type.replaceAll("_", " ")}</strong>
                      <span className="table-subtext">{activity.emission_factor.source_name}</span>
                      {activity.notes && <span className="table-subtext activity-notes-preview">{activity.notes}</span>}
                    </td>
                    <td><span className="category-pill">{activity.category.name}</span></td>
                    <td className="activity-number-cell">{formatQuantity(activity.quantity)} <span className="muted-inline">{activity.unit}</span></td>
                    <td className="activity-date-cell">{activity.activity_date}</td>
                    <td className="activity-number-cell"><strong>{formatCo2e(activity.calculated_co2e)}</strong></td>
                    <td className="activity-number-cell">{activity.unit_cost_ngn === null ? "—" : formatNaira(Number(activity.quantity) * Number(activity.unit_cost_ngn))}</td>
                    <td><div className="row-actions">
                      <button className="icon-button row-action" title="Edit activity" aria-label={`Edit ${activity.activity_type}`} onClick={() => { setEditing(activity); setEditorOpen(true); }}><Pencil size={15} /></button>
                      <button className="icon-button row-action delete-action" title="Delete activity" aria-label={`Delete ${activity.activity_type}`} onClick={() => void deleteActivity(activity)}><Trash2 size={15} /></button>
                    </div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="pagination-row">
          <span>Page {page + 1}</span>
          <div>
            <button className="button-secondary pagination-button" disabled={page === 0 || loading} onClick={() => changePage(Math.max(0, page - 1))}><ChevronLeft size={15} /> Previous</button>
            <button className="button-secondary pagination-button" disabled={!hasNextPage || loading} onClick={() => changePage(page + 1)}>Next <ChevronRight size={15} /></button>
          </div>
        </div>
      </section>

      {editorOpen && options && (
        <ActivityEditor
          key={editing?.id ?? "new-activity"}
          options={options}
          categories={options.categories}
          activity={editing}
          onClose={() => setEditorOpen(false)}
          onSaved={(activity) => {
            setEditorOpen(false);
            setLastSaved(activity);
            setPage(0);
            setReloadCount((current) => current + 1);
          }}
        />
      )}
    </div>
  );
}

export function ActivityEditor({
  options,
  categories,
  activity,
  onClose,
  onSaved,
}: {
  options: ActivityOptions;
  categories: CategoryOption[];
  activity: Activity | null;
  onClose: () => void;
  onSaved: (activity: Activity) => void;
}) {
  const initialCategoryId = activity?.category.id ?? categories[0]?.id ?? "";
  const [categoryId, setCategoryId] = useState(initialCategoryId);
  const [activityType, setActivityType] = useState(activity?.activity_type ?? "");
  const [unit, setUnit] = useState(activity?.unit ?? "");
  const [quantity, setQuantity] = useState(activity?.quantity ?? "");
  const [activityDate, setActivityDate] = useState(activity?.activity_date ?? new Date().toISOString().slice(0, 10));
  const [unitCostNgn, setUnitCostNgn] = useState(activity?.unit_cost_ngn ?? "");
  const [notes, setNotes] = useState(activity?.notes ?? "");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const selectedCategory = categories.find((category) => category.id === categoryId);
  const factors = options.emission_factors.filter((factor) => factor.category === selectedCategory?.name);
  const types = [...new Set(factors.map((factor) => factor.activity_type))].sort();
  const selectedActivityType = types.includes(activityType) ? activityType : types[0] ?? "";
  const units = [...new Set(factors.filter((factor) => factor.activity_type === selectedActivityType).map((factor) => factor.unit))].sort();
  const selectedUnit = units.includes(unit) ? unit : units[0] ?? "";
  const selectedFactor = factors.find(
    (factor) => factor.activity_type === selectedActivityType && factor.unit === selectedUnit,
  );
  const canTrackFuelPrice = [
    "car_petrol",
    "car_diesel",
    "generator_petrol",
    "generator_diesel",
    "cooking_lpg",
    "cooking_kerosene",
  ].includes(selectedActivityType);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    const payload: ActivityPayload = {
      category_id: categoryId,
      activity_type: selectedActivityType,
      quantity,
      unit: selectedUnit,
      activity_date: activityDate,
      unit_cost_ngn: canTrackFuelPrice && unitCostNgn !== "" ? unitCostNgn : null,
      notes: notes || null,
    };
    try {
      const saved = activity
        ? await api.updateActivity(activity.id, payload)
        : await api.createActivity(payload);
      onSaved(saved);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Activity could not be saved.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="activity-editor panel" role="dialog" aria-modal="true" aria-labelledby="activity-editor-title">
        <header className="editor-heading">
          <div><span className="section-kicker">{activity ? "Update record" : "New record"}</span><h2 id="activity-editor-title">{activity ? "Edit activity" : "Log an activity"}</h2></div>
          <button className="icon-button editor-close" aria-label="Close activity form" onClick={onClose}><X size={18} /></button>
        </header>
        <form className="editor-form" onSubmit={submit}>
          <label className="field-label">Category
            <select required value={categoryId} onChange={(event) => {
              const nextCategoryId = event.target.value;
              const nextCategory = categories.find((category) => category.id === nextCategoryId);
              const nextFactor = options.emission_factors.find((factor) => factor.category === nextCategory?.name);
              setCategoryId(nextCategoryId);
              setActivityType(nextFactor?.activity_type ?? "");
              setUnit(nextFactor?.unit ?? "");
              setUnitCostNgn("");
            }}>
              {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
            </select>
          </label>
          <div className="form-grid-two">
            <label className="field-label">Activity type
              <select required value={selectedActivityType} onChange={(event) => {
                const nextActivityType = event.target.value;
                const nextFactor = factors.find((factor) => factor.activity_type === nextActivityType);
                setActivityType(nextActivityType);
                setUnit(nextFactor?.unit ?? "");
                setUnitCostNgn("");
              }}>
                {types.map((type) => {
                  const factor = factors.find((option) => option.activity_type === type);
                  return <option key={type} value={type}>{factor?.activity_label ?? type.replaceAll("_", " ")}</option>;
                })}
              </select>
            </label>
            <label className="field-label">Unit
              <select required value={selectedUnit} onChange={(event) => setUnit(event.target.value)}>
                {units.map((option) => {
                  const factor = factors.find((item) => item.activity_type === selectedActivityType && item.unit === option);
                  return <option key={option} value={option}>{factor?.unit_label ?? option}</option>;
                })}
              </select>
            </label>
          </div>
          <div className="form-grid-two">
            <label className="field-label">Quantity ({selectedUnit})
              <input required type="number" min="0" step="any" value={quantity} onChange={(event) => setQuantity(event.target.value)} />
            </label>
            <label className="field-label">Activity date
              <input required type="date" value={activityDate} onChange={(event) => setActivityDate(event.target.value)} />
            </label>
          </div>
          {canTrackFuelPrice && (
            <label className="field-label">Price paid per {selectedUnit} (₦, optional)
              <input
                type="number"
                min="0"
                step="any"
                inputMode="decimal"
                value={unitCostNgn}
                onChange={(event) => setUnitCostNgn(event.target.value)}
                aria-describedby="fuel-price-hint"
              />
              <span className="field-hint" id="fuel-price-hint">Use your receipt or refill price. EcoTrack uses this only for your cost estimates.</span>
            </label>
          )}
          <label className="field-label">Notes <span className="muted-inline">Optional</span>
            <textarea rows={3} maxLength={10000} value={notes} onChange={(event) => setNotes(event.target.value)} />
          </label>
          <div className="calculation-note">
            {selectedFactor ? (
              <>
                Factor: <strong>{formatFactor(String(selectedFactor.factor_value))} kg CO₂e per {selectedFactor.unit}</strong>
                {" · "}<a href={selectedFactor.source_url ?? undefined} target="_blank" rel="noreferrer">{selectedFactor.source_name}</a>, {selectedFactor.source_year}
                {selectedFactor.region ? ` · ${selectedFactor.region}` : ""}
                {" · "}CO₂e is calculated after saving.
              </>
            ) : "CO₂e is calculated by EcoTrack from the selected activity factor after saving."}
          </div>
          {error && <div className="form-error" role="alert">{error}</div>}
          <div className="editor-actions">
            <button className="button-secondary" type="button" onClick={onClose}>Cancel</button>
            <button className="button-primary" type="submit" disabled={pending || !types.length || !units.length}>
              {pending ? "Saving…" : activity ? "Save changes" : "Save activity"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}