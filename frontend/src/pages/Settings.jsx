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

const IMPORT_SUMMARY_LABELS = {
  books: "Книги",
  reading_parts: "Части чтения",
  review_schedule_items: "Элементы повторений",
  review_attempts: "Попытки повторений",
  algorithm_groups: "Группы алгоритмов",
  algorithms: "Алгоритмы",
  algorithm_code_snippets: "Кодовые сниппеты",
  algorithm_review_items: "Алгоритмические повторения",
  algorithm_review_attempts: "Попытки алгоритмических повторений",
  algorithm_training_attempts: "Тренировочные попытки алгоритмов",
  user_settings: "Пользовательские настройки",
};

const formatImportSummaryLabel = (key) =>
  IMPORT_SUMMARY_LABELS[key] || "Данные профиля";

const formatImportWarning = (warning) => {
  if (typeof warning !== "string" || !warning.trim()) {
    return "Импорт завершен с предупреждением.";
  }

  const text = warning.trim();
  let match = text.match(
    /^Found (\d+) imported books matching existing titles\.$/i
  );
  if (match) {
    return `Найдено ${match[1]} импортированных книг с совпадающими названиями.`;
  }

  match = text.match(/^Imported books matching existing titles:\s*(.+)$/i);
  if (match) {
    return `Импортированные книги с совпадающими названиями: ${match[1]}.`;
  }

  match = text.match(
    /^Found (\d+) imported algorithm groups matching existing title_norm\.$/i
  );
  if (match) {
    return `Найдено ${match[1]} импортированных групп алгоритмов с совпадающими названиями.`;
  }

  match = text.match(
    /^Imported algorithm groups matching existing title_norm:\s*(.+)$/i
  );
  if (match) {
    return `Импортированные группы алгоритмов с совпадающими названиями: ${match[1]}.`;
  }

  match = text.match(
    /^Adjusted (\d+) algorithm group titles due to uniqueness constraint\.$/i
  );
  if (match) {
    return `Скорректировано названий групп алгоритмов из-за ограничения уникальности: ${match[1]}.`;
  }

  match = text.match(
    /^Adjusted algorithm group title '(.+)' to '(.+)' due to uniqueness constraint\.$/i
  );
  if (match) {
    return `Название группы алгоритмов изменено с «${match[1]}» на «${match[2]}» из-за ограничения уникальности.`;
  }

  if (/[A-Za-z]/.test(text)) {
    return "Импорт завершен с предупреждением. Проверьте данные профиля.";
  }

  return text;
};

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
            <h2>Резервное копирование и восстановление</h2>
            <p className="muted">
              Сохраните профиль в ZIP-архив или восстановите данные из ранее созданной
              резервной копии.
            </p>
          </div>
        </div>

        <div className="backup-sections">
          <div className="summary-card backup-card">
            <div className="backup-card-intro">
              <h3>Экспорт профиля</h3>
              <p className="muted">
                Скачайте ZIP-архив с данными профиля для переноса или резервной копии.
              </p>
            </div>
            <div className="form-actions backup-actions backup-card-actions backup-export-actions">
              <button
                className="ghost-button backup-action-button backup-action-secondary"
                type="button"
                disabled={exporting || importing}
                onClick={handleExport}
              >
                {exporting ? "Экспорт..." : "Скачать архив (.zip)"}
              </button>
            </div>
          </div>

          <div className="summary-card backup-card">
            <div className="backup-card-intro">
              <h3>Импорт профиля</h3>
              <p className="muted">
                Загрузите ZIP-архив для восстановления профиля в текущей установке.
              </p>
            </div>
            <ErrorBanner error={backupError} />

            <div className="backup-import-flow">
              <div className="form-block">
                <label>Файл архива</label>
                <input
                  ref={importFileInputRef}
                  id="profile-import-file"
                  className="backup-file-input"
                  type="file"
                  accept=".zip,application/zip"
                  onChange={handleFileChange}
                  disabled={importing}
                />
                <label
                  htmlFor="profile-import-file"
                  className={`backup-file-picker${importing ? " disabled" : ""}`}
                >
                  <span className="backup-file-button" aria-hidden="true">
                    Выбрать файл
                  </span>
                  <span className="backup-file-state">
                    {importFile ? `Выбран: ${importFile.name}` : "Файл не выбран"}
                  </span>
                </label>
              </div>

              <div className="form-block">
                <label>Режим импорта</label>
                <div className="backup-select-wrap">
                  <select
                    className="backup-mode-select"
                    value={importMode}
                    disabled={importing}
                    onChange={(event) => {
                      setImportMode(event.target.value);
                      if (event.target.value !== "replace") {
                        setConfirmReplace(false);
                      }
                    }}
                  >
                    <option value="merge">Объединить</option>
                    <option value="replace">Заменить</option>
                  </select>
                  <span className="backup-select-caret" aria-hidden="true">
                    v
                  </span>
                </div>

                <div className="backup-mode-help" aria-live="polite">
                  <p className={`backup-mode-help-item${importMode === "merge" ? " active" : ""}`}>
                    <strong>Объединить</strong> - добавляет данные, не удаляя существующие.
                  </p>
                  <p className={`backup-mode-help-item${importMode === "replace" ? " active warning" : ""}`}>
                    <strong>Заменить</strong> - полностью заменяет текущие данные.
                  </p>
                </div>
              </div>

              {importMode === "replace" && (
                <div className="backup-mode-warning" role="alert">
                  <span className="backup-mode-warning-icon" aria-hidden="true">
                    !
                  </span>
                  <span>
                    Режим «Заменить» удалит текущие данные перед восстановлением из архива.
                  </span>
                </div>
              )}

              {importMode === "replace" && (
                <label className="backup-confirm">
                  <input
                    type="checkbox"
                    checked={confirmReplace}
                    onChange={(event) => setConfirmReplace(event.target.checked)}
                  />
                  Я понимаю, что режим «Заменить» удалит текущие данные
                </label>
              )}
            </div>

            <div className="form-actions backup-actions backup-card-actions backup-import-actions">
              {importMode === "replace" && !confirmReplace && (
                <span className="muted backup-import-note">Для режима «Заменить» нужно подтверждение.</span>
              )}
              <button
                className="primary-button backup-action-button backup-action-primary"
                type="button"
                onClick={handleImport}
                disabled={importDisabled}
              >
                {importing ? "Импорт..." : "Импортировать"}
              </button>
            </div>

            {backupResult && (
              <div className="summary-card backup-summary">
                <h3>Результат импорта</h3>
                <div className="backup-columns">
                  <div>
                    <h4>Импортировано</h4>
                    <ul>
                      {Object.entries(backupResult.imported || {}).map(
                        ([key, value]) => (
                          <li key={key}>
                            <span>{formatImportSummaryLabel(key)}</span>
                            <strong>{value}</strong>
                          </li>
                        )
                      )}
                    </ul>
                  </div>

                  {Object.keys(backupResult.skipped || {}).length > 0 && (
                    <div>
                      <h4>Пропущено</h4>
                      <ul>
                        {Object.entries(backupResult.skipped || {}).map(
                          ([key, value]) => (
                            <li key={key}>
                              <span>{formatImportSummaryLabel(key)}</span>
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
                    <summary>Предупреждения ({backupResult.warnings.length})</summary>
                    <ul>
                      {backupResult.warnings.map((warning, index) => (
                        <li key={`${warning}-${index}`}>{formatImportWarning(warning)}</li>
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
                    Перезагрузить приложение
                  </button>
                </div>
              </div>
            )}
          </div>
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
