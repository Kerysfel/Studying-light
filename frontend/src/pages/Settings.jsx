import { useEffect, useMemo, useRef, useState } from "react";

import { downloadFile, request } from "../api.js";
import ErrorBanner from "../components/ErrorBanner.jsx";
import { getThemePreference, setThemePreference } from "../theme.js";

const formatExportFilename = () => {
  const now = new Date();
  const pad = (value) => String(value).padStart(2, "0");
  const stamp = [
    now.getFullYear(),
    pad(now.getMonth() + 1),
    pad(now.getDate()),
  ].join("");
  const time = [pad(now.getHours()), pad(now.getMinutes())].join("");
  return `studying-light-profile-${stamp}-${time}.zip`;
};

const toErrorObject = (error, fallbackCode = "UNKNOWN") => ({
  detail: error?.detail || "Ошибка запроса",
  code: error?.code || fallbackCode,
  errors: error?.errors || null,
});

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
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState("");
  const [themePreference, setThemePreferenceState] = useState(() =>
    getThemePreference()
  );

  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [backupError, setBackupError] = useState(null);
  const [backupResult, setBackupResult] = useState(null);
  const [importFile, setImportFile] = useState(null);
  const [importMode, setImportMode] = useState("merge");
  const [confirmReplace, setConfirmReplace] = useState(false);
  const importFileInputRef = useRef(null);

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
        setError(null);
      } catch (err) {
        if (!active) {
          return;
        }
        setError(toErrorObject(err));
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
    setError(null);
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
      setError(toErrorObject(err));
    } finally {
      setSaving(false);
    }
  };

  const handleThemeChange = (event) => {
    const nextPreference = setThemePreference(event.target.value);
    setThemePreferenceState(nextPreference);
  };

  const handleExport = async () => {
    setBackupError(null);
    try {
      setExporting(true);
      await downloadFile("/profile-export.zip", formatExportFilename());
    } catch (err) {
      setBackupError(toErrorObject(err));
    } finally {
      setExporting(false);
    }
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0] || null;
    setBackupError(null);
    setBackupResult(null);

    if (!file) {
      setImportFile(null);
      return;
    }

    if (!file.name.toLowerCase().endsWith(".zip")) {
      setImportFile(null);
      setBackupError({
        detail: "Можно импортировать только .zip файл.",
        code: "PROFILE_IMPORT_INVALID",
        errors: null,
      });
      return;
    }

    setImportFile(file);
  };

  const handleImport = async () => {
    if (importing) {
      return;
    }
    setBackupError(null);
    setBackupResult(null);

    if (!importFile) {
      setBackupError({
        detail: "Выберите .zip файл для импорта.",
        code: "PROFILE_IMPORT_INVALID",
      });
      return;
    }

    const formData = new FormData();
    formData.append("file", importFile);

    try {
      setImporting(true);
      const result = await request(
        `/profile-import?mode=${importMode}&confirm_replace=${confirmReplace}`,
        {
          method: "POST",
          body: formData,
        }
      );
      setBackupResult(result);
      setImportFile(null);
      setImportMode("merge");
      setConfirmReplace(false);
      if (importFileInputRef.current) {
        importFileInputRef.current.value = "";
      }
    } catch (err) {
      if (err?.code === "PROFILE_IMPORT_TOO_LARGE") {
        setBackupError({
          detail:
            "Файл слишком большой. Лимиты: архив до 200MB, распакованный объем до 400MB.",
          code: err.code,
          errors: err.errors || null,
        });
      } else {
        setBackupError(toErrorObject(err));
      }
    } finally {
      setImporting(false);
    }
  };

  const importDisabled = useMemo(() => {
    if (!importFile || importing) {
      return true;
    }
    if (importMode === "replace" && !confirmReplace) {
      return true;
    }
    return false;
  }, [confirmReplace, importFile, importMode, importing]);

  return (
    <div className="page-grid">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Тема интерфейса</h2>
            <p className="muted">
              Выберите светлую, тёмную или системную тему оформления.
            </p>
          </div>
        </div>
        <div className="form-grid">
          <div className="form-block">
            <label>Режим</label>
            <select value={themePreference} onChange={handleThemeChange}>
              <option value="system">Как в системе</option>
              <option value="light">Светлая</option>
              <option value="dark">Тёмная</option>
            </select>
          </div>
        </div>
      </section>

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
        <ErrorBanner error={error} />
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
            <h2>Backup / Restore</h2>
            <p className="muted">
              Экспортируйте профиль в ZIP и импортируйте его в другую установку.
            </p>
          </div>
        </div>

        <ErrorBanner error={backupError} />

        <div className="form-actions backup-actions">
          <button
            className="primary-button"
            type="button"
            disabled={exporting || importing}
            onClick={handleExport}
          >
            {exporting ? "Exporting..." : "Export profile (.zip)"}
          </button>
        </div>

        <div className="form-grid">
          <div className="form-block">
            <label>Файл архива</label>
            <input
              ref={importFileInputRef}
              type="file"
              accept=".zip,application/zip"
              onChange={handleFileChange}
            />
            <p className="muted backup-file-name">
              {importFile ? `Выбран: ${importFile.name}` : "Файл не выбран"}
            </p>
          </div>

          <div className="form-block">
            <label>Режим импорта</label>
            <select
              value={importMode}
              onChange={(event) => {
                setImportMode(event.target.value);
                if (event.target.value !== "replace") {
                  setConfirmReplace(false);
                }
              }}
            >
              <option value="merge">merge</option>
              <option value="replace">replace</option>
            </select>
          </div>

          {importMode === "replace" && (
            <label className="backup-confirm">
              <input
                type="checkbox"
                checked={confirmReplace}
                onChange={(event) => setConfirmReplace(event.target.checked)}
              />
              Я понимаю, что мои данные будут удалены
            </label>
          )}
        </div>

        <div className="form-actions backup-actions">
          <button
            className="primary-button"
            type="button"
            onClick={handleImport}
            disabled={importDisabled}
          >
            {importing ? "Importing..." : "Import"}
          </button>
          {importMode === "replace" && !confirmReplace && (
            <span className="muted">Для replace нужно подтверждение.</span>
          )}
        </div>

        {backupResult && (
          <div className="summary-card backup-summary">
            <h3>Import result</h3>
            <div className="backup-columns">
              <div>
                <h4>Imported</h4>
                <ul>
                  {Object.entries(backupResult.imported || {}).map(
                    ([key, value]) => (
                      <li key={key}>
                        <span>{key}</span>
                        <strong>{value}</strong>
                      </li>
                    )
                  )}
                </ul>
              </div>

              {Object.keys(backupResult.skipped || {}).length > 0 && (
                <div>
                  <h4>Skipped</h4>
                  <ul>
                    {Object.entries(backupResult.skipped || {}).map(
                      ([key, value]) => (
                        <li key={key}>
                          <span>{key}</span>
                          <strong>{value}</strong>
                        </li>
                      )
                    )}
                  </ul>
                </div>
              )}
            </div>

            {(backupResult.warnings || []).length > 0 && (
              <details className="backup-warnings">
                <summary>Warnings ({backupResult.warnings.length})</summary>
                <ul>
                  {backupResult.warnings.map((warning, index) => (
                    <li key={`${warning}-${index}`}>{warning}</li>
                  ))}
                </ul>
              </details>
            )}

            <div className="form-actions backup-actions">
              <button
                type="button"
                className="ghost-button"
                onClick={() => window.location.reload()}
              >
                Reload app
              </button>
            </div>
          </div>
        )}
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
