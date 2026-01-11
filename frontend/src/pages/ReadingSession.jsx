import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { getErrorMessage, request, requestText } from "../api.js";

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

const buildPomodoroPlan = (workGoalMinutes, workMinutes, breakMinutes) => {
  const safeTotal = Math.max(workGoalMinutes, 0);
  const safeWork = Math.max(workMinutes, 1);
  const safeBreak = Math.max(breakMinutes, 0);
  const segments = [];
  let remainingWork = safeTotal;
  let workTotal = 0;
  while (remainingWork > 0) {
    const duration = Math.min(safeWork, remainingWork);
    if (duration <= 0) {
      break;
    }
    workTotal += duration;
    segments.push({
      mode: "work",
      seconds: duration * 60,
    });
    remainingWork -= duration;
    if (remainingWork > 0 && safeBreak > 0) {
      segments.push({
        mode: "break",
        seconds: safeBreak * 60,
      });
    }
  }
  return { segments, workTotal };
};

const calculatePomodoroState = (segments, elapsedMs) => {
  if (!segments.length) {
    return {
      segmentIndex: 0,
      pomodoroSeconds: 0,
      mode: "work",
      sessionSeconds: 0,
      done: true,
    };
  }
  const safeElapsedMs = Math.max(elapsedMs, 0);
  let workSeconds = 0;
  let accumulatedMs = 0;
  for (let index = 0; index < segments.length; index += 1) {
    const segment = segments[index];
    const segmentMs = segment.seconds * 1000;
    const segmentEndMs = accumulatedMs + segmentMs;
    if (safeElapsedMs >= segmentEndMs) {
      if (segment.mode === "work") {
        workSeconds += segment.seconds;
      }
      accumulatedMs = segmentEndMs;
      continue;
    }
    const elapsedInSegmentMs = Math.max(0, safeElapsedMs - accumulatedMs);
    if (segment.mode === "work") {
      workSeconds += Math.floor(elapsedInSegmentMs / 1000);
    }
    const remainingMs = Math.max(segmentMs - elapsedInSegmentMs, 0);
    return {
      segmentIndex: index,
      pomodoroSeconds: Math.ceil(remainingMs / 1000),
      mode: segment.mode,
      sessionSeconds: workSeconds,
      done: false,
    };
  }
  return {
    segmentIndex: segments.length,
    pomodoroSeconds: 0,
    mode: segments[segments.length - 1].mode,
    sessionSeconds: workSeconds,
    done: true,
  };
};

const ReadingSession = () => {
  const [books, setBooks] = useState([]);
  const [selectedBook, setSelectedBook] = useState("");
  const [label, setLabel] = useState("");
  const [keywords, setKeywords] = useState("");
  const [terms, setTerms] = useState("");
  const [sentences, setSentences] = useState("");
  const [freeform, setFreeform] = useState("");
  const [codeText, setCodeText] = useState("");
  const [codeLanguage, setCodeLanguage] = useState("pseudo");
  const [pageEnd, setPageEnd] = useState("");
  const [activeTab, setActiveTab] = useState("keywords");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [createdPart, setCreatedPart] = useState(null);
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [showPromptModal, setShowPromptModal] = useState(false);
  const [copiedPrompt, setCopiedPrompt] = useState("");
  const [promptLoading, setPromptLoading] = useState(false);
  const [promptText, setPromptText] = useState("");
  const [algorithmPromptText, setAlgorithmPromptText] = useState("");
  const [promptPartIndex, setPromptPartIndex] = useState(null);

  const [pomodoroRunning, setPomodoroRunning] = useState(false);
  const [pomodoroMode, setPomodoroMode] = useState("work");
  const [pomodoroSeconds, setPomodoroSeconds] = useState(0);
  const [segmentIndex, setSegmentIndex] = useState(0);
  const [sessionSeconds, setSessionSeconds] = useState(0);
  const [settings, setSettings] = useState(null);
  const [lastPageEnd, setLastPageEnd] = useState(null);
  const [showLastPageNotice, setShowLastPageNotice] = useState(false);

  const keywordRef = useRef(null);
  const termsRef = useRef(null);
  const sentencesRef = useRef(null);
  const freeformRef = useRef(null);
  const codeRef = useRef(null);
  const elapsedMsRef = useRef(0);
  const lastTickRef = useRef(null);
  const sessionStartedRef = useRef(false);

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
    sessionStartedRef.current = false;
    setShowLastPageNotice(false);
    if (!selectedBook) {
      setLastPageEnd(null);
      return;
    }
    let active = true;
    const loadLastPage = async () => {
      try {
        const parts = await request(`/parts?book_id=${selectedBook}`);
        if (!active) {
          return;
        }
        let lastPage = null;
        parts.forEach((part) => {
          const value = part.page_end;
          if (typeof value !== "number" || !Number.isFinite(value)) {
            return;
          }
          if (lastPage === null || value > lastPage) {
            lastPage = value;
          }
        });
        setLastPageEnd(lastPage);
      } catch (err) {
        if (!active) {
          return;
        }
        setError(getErrorMessage(err));
      }
    };
    loadLastPage();
    return () => {
      active = false;
    };
  }, [selectedBook]);

  useEffect(() => {
    if (!showLastPageNotice) {
      return;
    }
    const timerId = setTimeout(() => {
      setShowLastPageNotice(false);
    }, 6000);
    return () => clearTimeout(timerId);
  }, [showLastPageNotice]);


  const sessionPlanMinutes = useMemo(() => {
    const day = new Date().getDay();
    const isWeekend = day === 0 || day === 6;
    const weekdayGoal = settings?.daily_goal_weekday_min || 40;
    const weekendGoal = settings?.daily_goal_weekend_min || 60;
    return isWeekend ? weekendGoal : weekdayGoal;
  }, [settings]);
  const sessionGoalMinutes = sessionPlanMinutes;

  const workMinutes = settings?.pomodoro_work_min || 25;
  const breakMinutes = settings?.pomodoro_break_min || 5;

  const pomodoroPlan = useMemo(
    () => buildPomodoroPlan(sessionPlanMinutes, workMinutes, breakMinutes),
    [sessionPlanMinutes, workMinutes, breakMinutes]
  );
  const planSegments = pomodoroPlan.segments;
  const sessionTargetMinutes = pomodoroPlan.workTotal;
  const planTotalMs = useMemo(
    () =>
      planSegments.reduce(
        (total, segment) => total + segment.seconds * 1000,
        0
      ),
    [planSegments]
  );

  useEffect(() => {
    if (!pomodoroRunning) {
      lastTickRef.current = null;
      return undefined;
    }
    lastTickRef.current = performance.now();
    const timerId = setInterval(() => {
      const now = performance.now();
      const lastTick = lastTickRef.current ?? now;
      const deltaMs = now - lastTick;
      lastTickRef.current = now;
      if (deltaMs <= 0 || planTotalMs <= 0) {
        return;
      }
      const nextElapsedMs = Math.min(
        planTotalMs,
        elapsedMsRef.current + deltaMs
      );
      elapsedMsRef.current = nextElapsedMs;
      const state = calculatePomodoroState(planSegments, nextElapsedMs);
      setPomodoroMode(state.mode);
      setPomodoroSeconds(state.pomodoroSeconds);
      setSegmentIndex(state.segmentIndex);
      setSessionSeconds(state.sessionSeconds);
      if (state.done) {
        setPomodoroRunning(false);
        sessionStartedRef.current = false;
      }
    }, 250);
    return () => clearInterval(timerId);
  }, [pomodoroRunning, planSegments, planTotalMs]);

  useEffect(() => {
    if (!planSegments.length) {
      elapsedMsRef.current = 0;
      const state = calculatePomodoroState([], 0);
      setPomodoroMode(state.mode);
      setPomodoroSeconds(state.pomodoroSeconds);
      setSegmentIndex(state.segmentIndex);
      setSessionSeconds(state.sessionSeconds);
      setPomodoroRunning(false);
      sessionStartedRef.current = false;
      return;
    }
    if (pomodoroRunning) {
      return;
    }
    const clampedElapsed = Math.min(elapsedMsRef.current, planTotalMs);
    elapsedMsRef.current = clampedElapsed;
    const state = calculatePomodoroState(planSegments, clampedElapsed);
    setPomodoroMode(state.mode);
    setPomodoroSeconds(state.pomodoroSeconds);
    setSegmentIndex(state.segmentIndex);
    setSessionSeconds(state.sessionSeconds);
  }, [planSegments, planTotalMs, pomodoroRunning]);

  useEffect(() => {
    const refMap = {
      keywords: keywordRef,
      terms: termsRef,
      sentences: sentencesRef,
      freeform: freeformRef,
      code: codeRef,
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

  const progressRatio = sessionTargetMinutes
    ? sessionSeconds / (sessionTargetMinutes * 60)
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
    { key: "code", label: "Код" },
  ];

  const filledTabs = {
    keywords: keywords.trim().length > 0,
    terms: terms.trim().length > 0,
    sentences: sentences.trim().length > 0,
    freeform: freeform.trim().length > 0,
    code: codeText.trim().length > 0,
  };

  const togglePomodoro = () => {
    if (pomodoroRunning) {
      setPomodoroRunning(false);
      return;
    }
    if (!planSegments.length) {
      return;
    }
    if (pomodoroSeconds === 0) {
      elapsedMsRef.current = 0;
      const state = calculatePomodoroState(planSegments, 0);
      setPomodoroMode(state.mode);
      setPomodoroSeconds(state.pomodoroSeconds);
      setSegmentIndex(state.segmentIndex);
      setSessionSeconds(state.sessionSeconds);
    }
    if (!sessionStartedRef.current) {
      if (lastPageEnd !== null) {
        setShowLastPageNotice(true);
      }
      sessionStartedRef.current = true;
    }
    setPomodoroRunning(true);
  };

  const resetPomodoro = () => {
    setPomodoroRunning(false);
    elapsedMsRef.current = 0;
    const state = calculatePomodoroState(planSegments, 0);
    setPomodoroMode(state.mode);
    setPomodoroSeconds(state.pomodoroSeconds);
    setSegmentIndex(state.segmentIndex);
    setSessionSeconds(state.sessionSeconds);
    sessionStartedRef.current = false;
    setShowLastPageNotice(false);
  };

  const totalCycles = useMemo(
    () => planSegments.filter((segment) => segment.mode === "work").length,
    [planSegments]
  );
  const currentCycle = useMemo(() => {
    if (!planSegments.length) {
      return 0;
    }
    let completed = 0;
    planSegments.slice(0, segmentIndex + 1).forEach((segment) => {
      if (segment.mode === "work") {
        completed += 1;
      }
    });
    return completed || 1;
  }, [planSegments, segmentIndex]);

  const buildSummaryPrompt = () => {
    if (!promptText) {
      return "";
    }
    const termLines = parseTerms(terms).map(
      (item) => `${item.term}${item.definition ? ` - ${item.definition}` : ""}`
    );
    const replacements = {
      book_title: selectedBookTitle || "-",
      part_index: promptPartIndex ? String(promptPartIndex) : "-",
      part_label: label.trim() || "-",
      notes_keywords: keywords
        ? keywords
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean)
            .join(", ")
        : "-",
      notes_terms: termLines.length > 0 ? termLines.join("\n") : "-",
      notes_sentences: splitLines(sentences).join("\n") || "-",
      notes_free: splitLines(freeform).join("\n") || "-",
    };
    let rendered = promptText;
    Object.entries(replacements).forEach(([key, value]) => {
      rendered = rendered.replaceAll(`{{${key}}}`, value);
    });
    return rendered;
  };

  const buildAlgorithmPrompt = () => {
    if (!algorithmPromptText) {
      return "";
    }
    const trimmedCode = codeText.trim();
    const replacements = {
      book_title: selectedBookTitle || "-",
      part_index: promptPartIndex ? String(promptPartIndex) : "-",
      part_label: label.trim() || "-",
      code_language: codeLanguage || "-",
      code_text: trimmedCode ? codeText : "-",
    };
    let rendered = algorithmPromptText;
    Object.entries(replacements).forEach(([key, value]) => {
      rendered = rendered.replaceAll(`{{${key}}}`, value);
    });
    return rendered;
  };

  const handleCopyPrompt = async (text, key) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedPrompt(key);
      setTimeout(() => setCopiedPrompt(""), 1600);
    } catch (err) {
      setError("Не удалось скопировать текст.");
    }
  };

  const openPromptModal = async () => {
    setCopiedPrompt("");
    setError("");
    if (!selectedBook) {
      setError("Выберите книгу для сессии.");
      return;
    }
    try {
      setPromptLoading(true);
      const hasCode = codeText.trim().length > 0;
      let template = "";
      let algorithmTemplate = "";
      let parts = [];
      if (hasCode) {
        [template, parts, algorithmTemplate] = await Promise.all([
          requestText("/prompts/generate_summary_and_questions"),
          request(`/parts?book_id=${selectedBook}`),
          requestText("/prompts/generate_algorithms_from_code"),
        ]);
      } else {
        [template, parts] = await Promise.all([
          requestText("/prompts/generate_summary_and_questions"),
          request(`/parts?book_id=${selectedBook}`),
        ]);
      }
      const maxIndex = parts.reduce(
        (maxValue, item) => Math.max(maxValue, item.part_index),
        0
      );
      setPromptPartIndex(maxIndex + 1);
      setPromptText(template);
      setAlgorithmPromptText(algorithmTemplate);
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

    const pageValue = pageEnd.trim();
    if (!pageValue) {
      setError("Укажите страницу, на которой остановились.");
      setShowSaveModal(false);
      return;
    }
    const pageEndValue = Number(pageValue);
    if (!Number.isInteger(pageEndValue) || pageEndValue <= 0) {
      setError("Страница должна быть положительным целым числом.");
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
      page_end: pageEndValue,
      session_seconds: sessionSeconds,
    };

    try {
      setSaving(true);
      const part = await request("/parts", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setCreatedPart(part);
      if (typeof part.page_end === "number" && Number.isFinite(part.page_end)) {
        setLastPageEnd(part.page_end);
      }
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
    setCodeText("");
    setCodeLanguage("pseudo");
    setPageEnd("");
    setCreatedPart(null);
    setSessionSeconds(0);
    elapsedMsRef.current = 0;
    sessionStartedRef.current = false;
    setShowLastPageNotice(false);
    resetPomodoro();
    setShowSaveModal(false);
  };

  const handleCodeKeyDown = (event) => {
    if (event.key !== "Tab") {
      return;
    }
    event.preventDefault();
    const target = event.currentTarget;
    const start = target.selectionStart ?? 0;
    const end = target.selectionEnd ?? 0;
    const value = target.value;
    const updated = `${value.slice(0, start)}    ${value.slice(end)}`;
    setCodeText(updated);
    requestAnimationFrame(() => {
      target.selectionStart = start + 4;
      target.selectionEnd = start + 4;
    });
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
              {pomodoroMode === "work" ? "Работа" : "Отдых"}
            </div>
            <div className="timer-meta">
              {totalCycles ? `Цикл ${currentCycle} из ${totalCycles}` : "Цикл -"}
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
              {formatClock(sessionSeconds)} / {sessionTargetMinutes} мин
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
        {showLastPageNotice && lastPageEnd !== null && (
          <div className="alert info">
            Вы остановились на странице №{lastPageEnd}.
          </div>
        )}
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
          {activeTab === "code" && (
            <div className="form-block full">
              <label>Язык кода</label>
              <select
                value={codeLanguage}
                onChange={(event) => setCodeLanguage(event.target.value)}
              >
                <option value="pseudo">pseudo</option>
                <option value="python">python</option>
                <option value="cpp">cpp</option>
                <option value="java">java</option>
                <option value="javascript">javascript</option>
                <option value="go">go</option>
              </select>
              <label>Код / псевдокод</label>
              <textarea
                className="code-area"
                rows="10"
                ref={codeRef}
                value={codeText}
                onChange={(event) => setCodeText(event.target.value)}
                onKeyDown={handleCodeKeyDown}
                placeholder="Вставьте или напишите код здесь"
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
                <label>Страница, на которой остановились</label>
                <input
                  type="number"
                  value={pageEnd}
                  onChange={(event) => setPageEnd(event.target.value)}
                  placeholder="120"
                  min="1"
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
                <p className="muted">Загрузка промптов...</p>
              ) : (
                <div className="prompt-grid">
                  <div className="prompt-block">
                    <div className="prompt-header">
                      <div className="prompt-title">
                        {codeText.trim()
                          ? "Промпт для повторений части (теория)"
                          : "Промпт для повторений части"}
                      </div>
                      <button
                        className="ghost-button"
                        type="button"
                        onClick={() =>
                          handleCopyPrompt(buildSummaryPrompt(), "summary")
                        }
                        disabled={promptLoading || !buildSummaryPrompt()}
                      >
                        {copiedPrompt === "summary"
                          ? "Скопировано"
                          : "Скопировать"}
                      </button>
                    </div>
                    <textarea
                      className="prompt-area"
                      rows="10"
                      value={buildSummaryPrompt()}
                      readOnly
                    />
                  </div>
                  {codeText.trim() && (
                    <div className="prompt-block">
                      <div className="prompt-header">
                        <div className="prompt-title">
                          Промпт для алгоритмов (из кода/псевдокода)
                        </div>
                        <button
                          className="ghost-button"
                          type="button"
                          onClick={() =>
                            handleCopyPrompt(
                              buildAlgorithmPrompt(),
                              "algorithm"
                            )
                          }
                          disabled={promptLoading || !buildAlgorithmPrompt()}
                        >
                          {copiedPrompt === "algorithm"
                            ? "Скопировано"
                            : "Скопировать"}
                        </button>
                      </div>
                      <textarea
                        className="prompt-area"
                        rows="10"
                        value={buildAlgorithmPrompt()}
                        readOnly
                      />
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReadingSession;
