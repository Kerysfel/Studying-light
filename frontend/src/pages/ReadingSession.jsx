import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { getErrorMessage, request, requestText } from "../api.js";

const TOTAL_CYCLES = 4;

const splitLines = (value) =>
  value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);

const parseTerms = (value) =>
  splitLines(value)
    .map((line) => {
      const separator = line.includes("—")
        ? "—"
        : line.includes(":")
        ? ":"
        : "-";
      const [term, ...rest] = line.split(separator);
      const definition = rest.join(separator).trim();
      return {
        term: term.trim(),
        definition: definition || null,
      };
    })
    .filter((item) => item.term);

const formatClock = (totalSeconds) => {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const padded = (value) => String(value).padStart(2, "0");
  if (hours > 0) {
    return `${padded(hours)}:${padded(minutes)}:${padded(seconds)}`;
  }
  return `${padded(minutes)}:${padded(seconds)}`;
};

const ReadingSession = () => {
  const [books, setBooks] = useState([]);
  const [selectedBook, setSelectedBook] = useState("");
  const [label, setLabel] = useState("");
  const [keywords, setKeywords] = useState("");
  const [terms, setTerms] = useState("");
  const [sentences, setSentences] = useState("");
  const [freeform, setFreeform] = useState("");
  const [pagesRead, setPagesRead] = useState("");
  const [activeTab, setActiveTab] = useState("keywords");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [createdPart, setCreatedPart] = useState(null);
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [showPromptModal, setShowPromptModal] = useState(false);
  const [copied, setCopied] = useState(false);
  const [promptLoading, setPromptLoading] = useState(false);
  const [promptText, setPromptText] = useState("");
  const [promptPartIndex, setPromptPartIndex] = useState(null);

  const [pomodoroRunning, setPomodoroRunning] = useState(false);
  const [pomodoroMode, setPomodoroMode] = useState("work");
  const [pomodoroSeconds, setPomodoroSeconds] = useState(0);
  const [cycle, setCycle] = useState(1);
  const [sessionSeconds, setSessionSeconds] = useState(0);
  const [settings, setSettings] = useState(null);

  const keywordRef = useRef(null);
  const termsRef = useRef(null);
  const sentencesRef = useRef(null);
  const freeformRef = useRef(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const [booksData, settingsData] = await Promise.all([
          request("/books"),
          request("/settings"),
        ]);
        if (!active) {
          return;
        }
        setBooks(booksData);
        setSettings(settingsData);
        const workMinutes = settingsData?.pomodoro_work_min || 25;
        setPomodoroSeconds(workMinutes * 60);
      } catch (err) {
        if (!active) {
          return;
        }
        setError(getErrorMessage(err));
      }
    };
    load();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!pomodoroRunning || pomodoroSeconds <= 0) {
      return undefined;
    }
    const timerId = setInterval(() => {
      setPomodoroSeconds((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(timerId);
  }, [pomodoroRunning, pomodoroSeconds]);

  useEffect(() => {
    if (!pomodoroRunning) {
      return;
    }
    const timerId = setInterval(() => {
      setSessionSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timerId);
  }, [pomodoroRunning]);

  useEffect(() => {
    if (!pomodoroRunning || pomodoroSeconds > 0) {
      return;
    }
    const workMinutes = settings?.pomodoro_work_min || 25;
    const breakMinutes = settings?.pomodoro_break_min || 5;
    if (pomodoroMode === "work") {
      if (cycle >= TOTAL_CYCLES) {
        setPomodoroRunning(false);
        return;
      }
      setPomodoroMode("break");
      setPomodoroSeconds(breakMinutes * 60);
      return;
    }
    setPomodoroMode("work");
    setPomodoroSeconds(workMinutes * 60);
    setCycle((prev) => Math.min(prev + 1, TOTAL_CYCLES));
  }, [pomodoroSeconds, pomodoroRunning, pomodoroMode, cycle, settings]);

  useEffect(() => {
    const refMap = {
      keywords: keywordRef,
      terms: termsRef,
      sentences: sentencesRef,
      freeform: freeformRef,
    };
    const ref = refMap[activeTab];
    if (ref?.current) {
      ref.current.focus();
    }
  }, [activeTab]);

  const activeBooks = useMemo(
    () => books.filter((book) => book.status !== "archived"),
    [books]
  );

  const selectedBookTitle = useMemo(() => {
    const book = books.find((item) => String(item.id) === selectedBook);
    return book ? book.title : "";
  }, [books, selectedBook]);

  const sessionGoalMinutes = useMemo(() => {
    const day = new Date().getDay();
    const isWeekend = day === 0 || day === 6;
    const weekdayGoal = settings?.daily_goal_weekday_min || 40;
    const weekendGoal = settings?.daily_goal_weekend_min || 60;
    return isWeekend ? weekendGoal : weekdayGoal;
  }, [settings]);

  const progressRatio = sessionGoalMinutes
    ? sessionSeconds / (sessionGoalMinutes * 60)
    : 0;
  const progressPercent = Math.min(progressRatio * 100, 100);
  let goalClass = "goal-low";
  if (progressRatio >= 1) {
    goalClass = "goal-high";
  } else if (progressRatio >= 0.5) {
    goalClass = "goal-mid";
  }

  const tabItems = [
    { key: "keywords", label: "Ключевые слова" },
    { key: "terms", label: "Термины" },
    { key: "sentences", label: "Важные предложения" },
    { key: "freeform", label: "Свободные заметки" },
  ];

  const filledTabs = {
    keywords: keywords.trim().length > 0,
    terms: terms.trim().length > 0,
    sentences: sentences.trim().length > 0,
    freeform: freeform.trim().length > 0,
  };

  const togglePomodoro = () => {
    if (pomodoroRunning) {
      setPomodoroRunning(false);
      return;
    }
    if (pomodoroSeconds === 0) {
      const workMinutes = settings?.pomodoro_work_min || 25;
      setPomodoroMode("work");
      setPomodoroSeconds(workMinutes * 60);
      setCycle(1);
    }
    setPomodoroRunning(true);
  };

  const resetPomodoro = () => {
    const workMinutes = settings?.pomodoro_work_min || 25;
    setPomodoroRunning(false);
    setPomodoroMode("work");
    setPomodoroSeconds(workMinutes * 60);
    setCycle(1);
  };

  const buildPrompt = () => {
    if (!promptText) {
      return "";
    }
    const termLines = parseTerms(terms).map(
      (item) => `${item.term}${item.definition ? ` - ${item.definition}` : ""}`
    );
    const replacements = {
      book_title: selectedBookTitle || "-",
      part_index: promptPartIndex ? String(promptPartIndex) : "-",
      label: label.trim() || "-",
      keywords: keywords
        ? keywords
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean)
            .join(", ")
        : "-",
      terms: termLines.length > 0 ? termLines.join("\n") : "-",
      sentences: splitLines(sentences).join("\n") || "-",
      freeform: splitLines(freeform).join("\n") || "-",
    };
    let rendered = promptText;
    Object.entries(replacements).forEach(([key, value]) => {
      rendered = rendered.replaceAll(`{{${key}}}`, value);
    });
    return rendered;
  };

  const handleCopyPrompt = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch (err) {
      setError("Не удалось скопировать текст.");
    }
  };

  const openPromptModal = async () => {
    setCopied(false);
    setError("");
    if (!selectedBook) {
      setError("Выберите книгу для сессии.");
      return;
    }
    try {
      setPromptLoading(true);
      const [template, parts] = await Promise.all([
        requestText("/prompts/generate_summary_and_questions"),
        request(`/parts?book_id=${selectedBook}`),
      ]);
      const maxIndex = parts.reduce(
        (maxValue, item) => Math.max(maxValue, item.part_index),
        0
      );
      setPromptPartIndex(maxIndex + 1);
      setPromptText(template);
      setShowPromptModal(true);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setPromptLoading(false);
    }
  };

  const handleSaveSession = async () => {
    setError("");
    if (!selectedBook) {
      setError("Выберите книгу для сессии.");
      setShowSaveModal(false);
      return;
    }

    const pagesValue = pagesRead.trim();
    const pagesReadValue = pagesValue ? Number(pagesValue) : null;
    if (
      pagesValue &&
      (!Number.isInteger(pagesReadValue) || pagesReadValue < 0)
    ) {
      setError("Прочитанные страницы должны быть нулем или положительным числом.");
      setShowSaveModal(false);
      return;
    }

    const payload = {
      book_id: Number(selectedBook),
      label: label.trim() || null,
      raw_notes: {
        keywords: keywords
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        terms: parseTerms(terms),
        sentences: splitLines(sentences),
        freeform: splitLines(freeform),
      },
      pages_read: pagesReadValue,
      session_seconds: sessionSeconds,
    };

    try {
      setSaving(true);
      const part = await request("/parts", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setCreatedPart(part);
      localStorage.setItem("lastPartId", String(part.id));
      setShowSaveModal(false);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteSession = () => {
    setSelectedBook("");
    setLabel("");
    setKeywords("");
    setTerms("");
    setSentences("");
    setFreeform("");
    setPagesRead("");
    setCreatedPart(null);
    setSessionSeconds(0);
    resetPomodoro();
    setShowSaveModal(false);
  };

  return (
    <div className="page-grid">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Сессия чтения</h2>
            <p className="muted">Помодоро и общий таймер сессии.</p>
          </div>
          <span className="badge">
            {pomodoroMode === "work" ? "Фокус" : "Перерыв"}
          </span>
        </div>
        <div className="timer-grid">
          <div className="timer-card">
            <div className="timer-count">{formatClock(pomodoroSeconds)}</div>
            <div className="timer-meta">
              Цикл {cycle} из {TOTAL_CYCLES}
            </div>
            <div className="timer-actions">
              <button className="primary-button" type="button" onClick={togglePomodoro}>
                {pomodoroRunning ? "Пауза" : "Старт"}
              </button>
              <button className="ghost-button" type="button" onClick={resetPomodoro}>
                Сброс
              </button>
            </div>
          </div>

          <div className="session-card">
            <div className="session-title">Таймер сессии</div>
            <div className="session-time">
              {formatClock(sessionSeconds)} / {sessionGoalMinutes} мин
            </div>
            <div className={`goal-indicator ${goalClass}`}>
              <div className="goal-label">
                Цель на день: {sessionGoalMinutes} минут
              </div>
              <div className="progress-track">
                <div
                  className="progress-bar"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>
            <div className="session-hint">
              {progressRatio >= 1
                ? "Цель выполнена. Можно закончить на сегодня."
                : "Двигайтесь маленькими блоками, это работает."}
            </div>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Часть и заметки</h2>
            <p className="muted">Сохраняйте результат сессии сразу.</p>
          </div>
        </div>
        {error && <div className="alert error">{error}</div>}
        <div className="form-grid">
          <div className="form-block">
            <label>Книга</label>
            <select
              value={selectedBook}
              onChange={(event) => setSelectedBook(event.target.value)}
            >
              <option value="">Выберите книгу</option>
              {activeBooks.map((book) => (
                <option key={book.id} value={book.id}>
                  {book.title}
                </option>
              ))}
            </select>
            {activeBooks.length === 0 && (
              <div className="empty-state">
                Нет активных книг. Добавьте книгу перед сессией.
                <Link className="inline-link" to="/books">
                  Перейти к книгам
                </Link>
              </div>
            )}
          </div>
          <div className="form-block">
            <label>Метка части</label>
            <input
              value={label}
              onChange={(event) => setLabel(event.target.value)}
              placeholder="Например, Гл. 3-4"
            />
          </div>
        </div>

        <div className="tabs">
          {tabItems.map((tab) => (
            <button
              key={tab.key}
              className={`tab-button${activeTab === tab.key ? " active" : ""}${
                filledTabs[tab.key] ? " filled" : ""
              }`}
              type="button"
              onClick={() => setActiveTab(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="tab-panel">
          {activeTab === "keywords" && (
            <div className="form-block full">
              <label>Ключевые слова</label>
              <input
                ref={keywordRef}
                value={keywords}
                onChange={(event) => setKeywords(event.target.value)}
                placeholder="слово, слово"
              />
            </div>
          )}
          {activeTab === "terms" && (
            <div className="form-block full">
              <label>Термины (каждый с новой строки)</label>
              <textarea
                rows="5"
                ref={termsRef}
                value={terms}
                onChange={(event) => setTerms(event.target.value)}
                placeholder="Термин — определение"
              />
            </div>
          )}
          {activeTab === "sentences" && (
            <div className="form-block full">
              <label>Важные предложения</label>
              <textarea
                rows="5"
                ref={sentencesRef}
                value={sentences}
                onChange={(event) => setSentences(event.target.value)}
                placeholder="Одно предложение в строке"
              />
            </div>
          )}
          {activeTab === "freeform" && (
            <div className="form-block full">
              <label>Свободные заметки</label>
              <textarea
                rows="5"
                ref={freeformRef}
                value={freeform}
                onChange={(event) => setFreeform(event.target.value)}
                placeholder="Короткие пункты или фразы"
              />
            </div>
          )}
        </div>

        <div className="form-actions">
          <button
            className="ghost-button"
            type="button"
            onClick={openPromptModal}
          >
            Сгенерировать промпт
          </button>
          <button
            className="primary-button"
            type="button"
            onClick={() => setShowSaveModal(true)}
            disabled={saving}
          >
            {saving ? "Сохранение..." : "Закрыть сессию"}
          </button>
        </div>

        {createdPart && (
          <div className="success-block">
            <div className="success-title">Часть сохранена</div>
            <div className="success-detail">
              Часть #{createdPart.part_index} добавлена. Продолжите импорт JSON.
            </div>
            <Link className="primary-button" to="/import">
              Перейти к импорту
            </Link>
          </div>
        )}
      </section>

      {showSaveModal && (
        <div className="modal-backdrop">
          <div className="modal">
            <div className="modal-header">
              <div>
                <h2>Закрыть сессию</h2>
                <p className="muted">
                  Сохранить часть или удалить заметки без сохранения?
                </p>
              </div>

              <button
                className="ghost-button"
                type="button"
                onClick={() => setShowSaveModal(false)}
              >
                Отмена
              </button>
            </div>
            <div className="modal-body">
              <div className="form-block full">
                <label>Прочитано страниц (необязательно)</label>
                <input
                  type="number"
                  value={pagesRead}
                  onChange={(event) => setPagesRead(event.target.value)}
                  placeholder="20"
                  min="0"
                />
              </div>
            </div>
            <div className="modal-actions">
              <button
                className="danger-button"
                type="button"
                onClick={handleDeleteSession}
              >
                Удалить
              </button>
              <button
                className="primary-button"
                type="button"
                onClick={handleSaveSession}
                disabled={saving}
              >
                {saving ? "Сохранение..." : "Сохранить"}
              </button>
            </div>
          </div>
        </div>
      )}

      {showPromptModal && (
        <div className="modal-backdrop">
          <div className="modal">
            <div className="modal-header">
              <div>
                <h2>Промпт для GPT</h2>
                <p className="muted">Скопируйте текст и вставьте в чат.</p>
              </div>
              <button
                className="ghost-button"
                type="button"
                onClick={() => setShowPromptModal(false)}
              >
                Закрыть
              </button>
            </div>
            <div className="modal-body">
              {promptLoading ? (
                <p className="muted">Подготовка промпта...</p>
              ) : (
                <textarea
                  className="prompt-area"
                  rows="10"
                  value={buildPrompt()}
                  readOnly
                />
              )}
              <div className="modal-actions">
                <button
                  className="primary-button"
                  type="button"
                  onClick={() => handleCopyPrompt(buildPrompt())}
                  disabled={promptLoading || !buildPrompt()}
                >
                  {copied ? "Скопировано" : "Копировать"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReadingSession;
