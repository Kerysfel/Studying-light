import { useEffect, useState } from "react";

import { getErrorMessage, request } from "../api.js";

const Settings = () => {
  const [form, setForm] = useState({
    daily_goal_weekday_min: "",
    daily_goal_weekend_min: "",
    pomodoro_work_min: "",
    pomodoro_break_min: "",
  });
  const [intervals, setIntervals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        setLoading(true);
        const data = await request("/settings");
        if (!active) {
          return;
        }
        setForm({
          daily_goal_weekday_min: data.daily_goal_weekday_min?.toString() || "",
          daily_goal_weekend_min: data.daily_goal_weekend_min?.toString() || "",
          pomodoro_work_min: data.pomodoro_work_min?.toString() || "",
          pomodoro_break_min: data.pomodoro_break_min?.toString() || "",
        });
        setIntervals(data.intervals_days || []);
        setError("");
      } catch (err) {
        if (!active) {
          return;
        }
        setError(getErrorMessage(err));
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };
    load();
    return () => {
      active = false;
    };
  }, []);

  const updateField = (field) => (event) => {
    setForm((prev) => ({ ...prev, [field]: event.target.value }));
  };

  const normalizeNumber = (value) => {
    const trimmed = value.trim();
    if (!trimmed) {
      return null;
    }
    const parsed = Number(trimmed);
    return Number.isFinite(parsed) ? parsed : null;
  };

  const handleSave = async () => {
    setError("");
    setSuccess("");
    const payload = {
      daily_goal_weekday_min: normalizeNumber(form.daily_goal_weekday_min),
      daily_goal_weekend_min: normalizeNumber(form.daily_goal_weekend_min),
      pomodoro_work_min: normalizeNumber(form.pomodoro_work_min),
      pomodoro_break_min: normalizeNumber(form.pomodoro_break_min),
    };

    try {
      setSaving(true);
      const data = await request("/settings", {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      setForm({
        daily_goal_weekday_min: data.daily_goal_weekday_min?.toString() || "",
        daily_goal_weekend_min: data.daily_goal_weekend_min?.toString() || "",
        pomodoro_work_min: data.pomodoro_work_min?.toString() || "",
        pomodoro_break_min: data.pomodoro_break_min?.toString() || "",
      });
      setIntervals(data.intervals_days || []);
      setSuccess("Настройки сохранены.");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-grid">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Настройки сессии</h2>
            <p className="muted">
              Обновите дневные цели и длительности помодоро.
            </p>
          </div>
        </div>
        {loading && <p className="muted">Загрузка настроек...</p>}
        {error && <div className="alert error">{error}</div>}
        {success && <div className="alert success">{success}</div>}
        <div className="form-grid">
          <div className="form-block">
            <label>Цель в будни (мин)</label>
            <input
              type="number"
              value={form.daily_goal_weekday_min}
              onChange={updateField("daily_goal_weekday_min")}
              placeholder="40"
              min="1"
            />
          </div>
          <div className="form-block">
            <label>Цель в выходные (мин)</label>
            <input
              type="number"
              value={form.daily_goal_weekend_min}
              onChange={updateField("daily_goal_weekend_min")}
              placeholder="60"
              min="1"
            />
          </div>
          <div className="form-block">
            <label>Помодоро: работа (мин)</label>
            <input
              type="number"
              value={form.pomodoro_work_min}
              onChange={updateField("pomodoro_work_min")}
              placeholder="25"
              min="1"
            />
          </div>
          <div className="form-block">
            <label>Помодоро: перерыв (мин)</label>
            <input
              type="number"
              value={form.pomodoro_break_min}
              onChange={updateField("pomodoro_break_min")}
              placeholder="5"
              min="1"
            />
          </div>
        </div>
        <div className="form-actions">
          <button
            className="primary-button"
            type="button"
            onClick={handleSave}
            disabled={saving || loading}
          >
            {saving ? "Сохранение..." : "Сохранить настройки"}
          </button>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Интервалы</h2>
            <p className="muted">Текущие интервалы повторений.</p>
          </div>
        </div>
        <div className="pill-row">
          {intervals.map((value) => (
            <span key={value} className="pill">
              {value} д
            </span>
          ))}
        </div>
      </section>
    </div>
  );
};

export default Settings;
