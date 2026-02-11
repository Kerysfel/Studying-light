import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getErrorMessage, request, requestText } from "../api.js";
import ErrorBanner from "../components/ErrorBanner.jsx";

const AlgorithmDetail = () => {
  const { id } = useParams();
  const [algorithm, setAlgorithm] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copyState, setCopyState] = useState({ id: null, message: "" });
  const [bookTitles, setBookTitles] = useState(new Map());
  const [trainingVisible, setTrainingVisible] = useState(false);
  const [trainingMode, setTrainingMode] = useState("memory");
  const [trainingCode, setTrainingCode] = useState("");
  const [trainingDiff, setTrainingDiff] = useState([]);
  const [showDiff, setShowDiff] = useState(false);
  const [typingInput, setTypingInput] = useState("");
  const [typingStartedAt, setTypingStartedAt] = useState(null);
  const [typingElapsed, setTypingElapsed] = useState(0);
  const [typingAccuracy, setTypingAccuracy] = useState(0);
  const [typingSpeed, setTypingSpeed] = useState(0);
  const [typingDiff, setTypingDiff] = useState([]);
  const [typingSaveError, setTypingSaveError] = useState(null);
  const [typingSaveSuccess, setTypingSaveSuccess] = useState("");
  const typingRef = useRef(null);
  const typingOverlayRef = useRef(null);
  const typingBackRef = useRef(null);
  const [trainingError, setTrainingError] = useState(null);
  const [promptTemplate, setPromptTemplate] = useState("");
  const [promptLoading, setPromptLoading] = useState(false);
  const [promptCopied, setPromptCopied] = useState(false);
  const [gptJsonInput, setGptJsonInput] = useState("");
  const [trainingSaving, setTrainingSaving] = useState(false);
  const [trainingSaveError, setTrainingSaveError] = useState(null);
  const [trainingSaveSuccess, setTrainingSaveSuccess] = useState("");
  const [trainingAttempts, setTrainingAttempts] = useState([]);
  const [attemptsLoading, setAttemptsLoading] = useState(false);
  const [attemptsError, setAttemptsError] = useState(null);
  const [attemptModeFilter, setAttemptModeFilter] = useState("all");
  const codeInputRef = useRef(null);

  const toError = (detail, code = "UNKNOWN", errors = null) => ({
    detail,
    code,
    errors,
  });

  useEffect(() => {
    let active = true;
    const loadAlgorithm = async () => {
      try {
        setLoading(true);
        setError("");
        const data = await request(`/algorithms/${id}`);
        if (!active) {
          return;
        }
        setAlgorithm(data);
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
    loadAlgorithm();
    return () => {
      active = false;
    };
  }, [id]);

  useEffect(() => {
    setTrainingCode("");
    setTrainingDiff([]);
    setShowDiff(false);
    setTrainingError(null);
    setTrainingSaveError(null);
    setTrainingSaveSuccess("");
    setGptJsonInput("");
    resetTyping();
    setTrainingMode("memory");
    setAttemptModeFilter("all");
  }, [id]);

  useEffect(() => {
    let active = true;
    const loadBooks = async () => {
      if (!algorithm?.source_part?.book_id) {
        return;
      }
      try {
        const data = await request("/books");
        if (!active) {
          return;
        }
        const map = new Map();
        data.forEach((book) => {
          map.set(book.id, book.title);
        });
        setBookTitles(map);
      } catch (err) {
        if (!active) {
          return;
        }
        setBookTitles(new Map());
      }
    };
    loadBooks();
    return () => {
      active = false;
    };
  }, [algorithm]);

  const loadTrainings = async () => {
    try {
      setAttemptsLoading(true);
      setAttemptsError(null);
      const data = await request(`/algorithm-trainings?algorithm_id=${id}`);
      setTrainingAttempts(Array.isArray(data) ? data.slice(0, 50) : []);
    } catch (err) {
      setTrainingAttempts([]);
      setAttemptsError(
        toError(
          err?.detail || "Не удалось загрузить историю тренировок",
          err?.code || "UNKNOWN",
          err?.errors || null
        )
      );
    } finally {
      setAttemptsLoading(false);
    }
  };

  useEffect(() => {
    if (!id) {
      return;
    }
    loadTrainings();
  }, [id]);

  const sourceInfo = useMemo(() => {
    if (!algorithm?.source_part) {
      return null;
    }
    const part = algorithm.source_part;
    const title = bookTitles.get(part.book_id);
    return {
      partIndex: part.part_index,
      bookTitle: title || `Книга #${part.book_id}`,
    };
  }, [algorithm, bookTitles]);

  const referenceSnippet = useMemo(() => {
    if (!algorithm?.code_snippets?.length) {
      return null;
    }
    return (
      algorithm.code_snippets.find((snippet) => snippet.is_reference) ||
      algorithm.code_snippets[0]
    );
  }, [algorithm]);

  const formatDateTime = (value) => {
    if (!value) {
      return "-";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return date.toLocaleString();
  };

  const latestTraining = trainingAttempts[0] || null;
  const latestGpt = latestTraining?.gpt_check_json || null;
  const latestOverall = latestGpt?.overall || null;
  const latestItems = Array.isArray(latestGpt?.items) ? latestGpt.items : [];

  const filteredAttempts = useMemo(() => {
    if (attemptModeFilter === "all") {
      return trainingAttempts;
    }
    return trainingAttempts.filter((attempt) => attempt.mode === attemptModeFilter);
  }, [attemptModeFilter, trainingAttempts]);

  const trainingStats = useMemo(() => {
    const attemptsTotal = trainingAttempts.length;
    const lastAttemptAt = trainingAttempts[0]?.created_at || null;

    const ratedAttempts = trainingAttempts.filter(
      (item) => typeof item.rating_1_to_5 === "number"
    );
    const avgRating =
      ratedAttempts.length > 0
        ? (
            ratedAttempts.reduce((sum, item) => sum + item.rating_1_to_5, 0) /
            ratedAttempts.length
          ).toFixed(2)
        : null;

    const typingAttempts = trainingAttempts.filter((item) => item.mode === "typing");
    const typingWithAccuracy = typingAttempts.filter(
      (item) => typeof item.accuracy === "number"
    );
    const avgAccuracy =
      typingWithAccuracy.length > 0
        ? (
            typingWithAccuracy.reduce((sum, item) => sum + item.accuracy, 0) /
            typingWithAccuracy.length
          ).toFixed(1)
        : null;
    const bestAccuracy =
      typingWithAccuracy.length > 0
        ? Math.max(...typingWithAccuracy.map((item) => item.accuracy)).toFixed(1)
        : null;
    const totalDurationSec = typingAttempts.reduce(
      (sum, item) => sum + (typeof item.duration_sec === "number" ? item.duration_sec : 0),
      0
    );

    return {
      attemptsTotal,
      lastAttemptAt,
      avgRating,
      avgAccuracy,
      bestAccuracy,
      totalDurationSec,
    };
  }, [trainingAttempts]);

  const handleCopy = async (snippetId, text) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopyState({ id: snippetId, message: "Скопировано" });
      setTimeout(() => setCopyState({ id: null, message: "" }), 1500);
    } catch (err) {
      setCopyState({ id: snippetId, message: "Не удалось скопировать" });
      setTimeout(() => setCopyState({ id: null, message: "" }), 1500);
    }
  };

  const handleCodeKeyDown = (event) => {
    if (event.key !== "Tab") {
      return;
    }
    event.preventDefault();
    const target = event.target;
    const start = target.selectionStart || 0;
    const end = target.selectionEnd || 0;
    const insert = "    ";
    const nextValue =
      trainingCode.slice(0, start) + insert + trainingCode.slice(end);
    setTrainingCode(nextValue);
    requestAnimationFrame(() => {
      if (codeInputRef.current) {
        codeInputRef.current.selectionStart = start + insert.length;
        codeInputRef.current.selectionEnd = start + insert.length;
      }
    });
  };

  const buildDiff = (expected, actual) => {
    const expectedLines = expected.split(/\r?\n/);
    const actualLines = actual.split(/\r?\n/);
    const max = Math.max(expectedLines.length, actualLines.length);
    const rows = [];
    for (let index = 0; index < max; index += 1) {
      const left = actualLines[index] ?? "";
      const right = expectedLines[index] ?? "";
      let type = "same";
      if (left === right) {
        type = "same";
      } else if (!left && right) {
        type = "missing";
      } else if (left && !right) {
        type = "extra";
      } else {
        type = "changed";
      }
      rows.push({ index: index + 1, left, right, type });
    }
    return rows;
  };

  const syncTypingScroll = () => {
    if (!typingRef.current) {
      return;
    }
    const { scrollTop, scrollLeft } = typingRef.current;
    if (typingOverlayRef.current) {
      typingOverlayRef.current.scrollTop = scrollTop;
      typingOverlayRef.current.scrollLeft = scrollLeft;
    }
    if (typingBackRef.current) {
      typingBackRef.current.scrollTop = scrollTop;
      typingBackRef.current.scrollLeft = scrollLeft;
    }
  };

  const computeTypingMetrics = (value, startedAt) => {
    const reference = referenceSnippet?.code_text || "";
    const maxLength = Math.max(reference.length, value.length);
    let correct = 0;
    let wrong = 0;
    const diffRows = [];
    for (let index = 0; index < maxLength; index += 1) {
      const expected = reference[index] || "";
      const actual = value[index] || "";
      let status = "pending";
      if (actual) {
        if (actual === expected) {
          status = "correct";
          correct += 1;
        } else {
          status = "wrong";
          wrong += 1;
        }
      } else if (expected) {
        status = "pending";
      }
      diffRows.push({ expected, actual, status });
    }
    const totalTyped = value.length;
    const accuracy =
      totalTyped > 0 ? Math.round((correct / totalTyped) * 1000) / 10 : 0;
    const elapsedSec = startedAt
      ? Math.max((Date.now() - startedAt) / 1000, 0)
      : 0;
    const cps = elapsedSec > 0 ? Math.round((totalTyped / elapsedSec) * 10) / 10 : 0;
    return {
      accuracy,
      elapsedSec,
      cps,
      diffRows,
    };
  };

  const handleTypingInput = (event) => {
    const value = event.target.value;
    const startedAt = typingStartedAt ?? Date.now();
    if (!typingStartedAt) {
      setTypingStartedAt(startedAt);
    }
    setTypingInput(value);
    const metrics = computeTypingMetrics(value, startedAt);
    setTypingAccuracy(metrics.accuracy);
    setTypingElapsed(metrics.elapsedSec);
    setTypingSpeed(metrics.cps);
    setTypingDiff(metrics.diffRows);
    syncTypingScroll();
  };

  const handleTypingKeyDown = (event) => {
    if (event.key !== "Tab") {
      return;
    }
    event.preventDefault();
    const target = event.target;
    const start = target.selectionStart || 0;
    const end = target.selectionEnd || 0;
    const insert = "    ";
    const nextValue =
      typingInput.slice(0, start) + insert + typingInput.slice(end);
    const startedAt = typingStartedAt ?? Date.now();
    if (!typingStartedAt) {
      setTypingStartedAt(startedAt);
    }
    setTypingInput(nextValue);
    const metrics = computeTypingMetrics(nextValue, startedAt);
    setTypingAccuracy(metrics.accuracy);
    setTypingElapsed(metrics.elapsedSec);
    setTypingSpeed(metrics.cps);
    setTypingDiff(metrics.diffRows);
    requestAnimationFrame(() => {
      if (typingRef.current) {
        typingRef.current.selectionStart = start + insert.length;
        typingRef.current.selectionEnd = start + insert.length;
      }
    });
  };

  const resetTyping = () => {
    setTypingInput("");
    setTypingStartedAt(null);
    setTypingElapsed(0);
    setTypingAccuracy(0);
    setTypingSpeed(0);
    setTypingDiff([]);
    setTypingSaveError(null);
    setTypingSaveSuccess("");
  };

  const handleSaveTyping = async () => {
    setTypingSaveError(null);
    setTypingSaveSuccess("");
    if (!typingInput.trim()) {
      setTypingSaveError(toError("Введите код для сохранения результата.", "VALIDATION_ERROR"));
      return;
    }
    const duration = Math.max(Math.round(typingElapsed), 1);
    try {
      setTrainingSaving(true);
      await request("/algorithm-trainings", {
        method: "POST",
        body: JSON.stringify({
          algorithm_id: Number(id),
          mode: "typing",
          code_text: typingInput,
          accuracy: typingAccuracy,
          duration_sec: duration,
        }),
      });
      await loadTrainings();
      setTypingSaveSuccess("Результат сохранён.");
    } catch (err) {
      setTypingSaveError(
        toError(err?.detail || "Не удалось сохранить результат", err?.code || "UNKNOWN", err?.errors || null)
      );
    } finally {
      setTrainingSaving(false);
    }
  };

  const handleCompare = () => {
    setTrainingError(null);
    if (!referenceSnippet?.code_text) {
      setTrainingError(toError("Нет эталонного кода для сравнения.", "BAD_REQUEST"));
      return;
    }
    if (!trainingCode.trim()) {
      setTrainingError(toError("Введите код для сравнения.", "VALIDATION_ERROR"));
      return;
    }
    const diffRows = buildDiff(referenceSnippet.code_text, trainingCode);
    setTrainingDiff(diffRows);
    setShowDiff(true);
  };

  const ensurePromptTemplate = async () => {
    if (promptTemplate) {
      return promptTemplate;
    }
    setPromptLoading(true);
    try {
      const template = await requestText("/prompts/check_algorithm_answers");
      setPromptTemplate(template);
      return template;
    } finally {
      setPromptLoading(false);
    }
  };

  const buildTrainingPrompt = async () => {
    const template = await ensurePromptTemplate();
    if (!template || !algorithm) {
      return "";
    }
    const reviewDate = new Date().toISOString().slice(0, 10);
    const invariantsText = (algorithm.invariants || [])
      .map((item) => `- ${item}`)
      .join("\n");
    const stepsText = (algorithm.steps || [])
      .map((item) => `- ${item}`)
      .join("\n");
    const cornerCasesText = (algorithm.corner_cases || [])
      .map((item) => `- ${item}`)
      .join("\n");
    const referenceBlock = referenceSnippet?.code_text
      ? `\n\nЭталон:\n\`\`\`\n${referenceSnippet.code_text}\n\`\`\`\n`
      : "";
    const qaBlock = `Вопрос: Восстановите код алгоритма.${referenceBlock}\nОтвет: ${
      trainingCode.trim() || "-"
    }`;
    const replacements = {
      group_title: algorithm.group_title || "-",
      algorithm_title: algorithm.title || "-",
      interval_days: "null",
      review_date: reviewDate,
      summary: algorithm.summary || "-",
      when_to_use: algorithm.when_to_use || "-",
      complexity: algorithm.complexity || "-",
      invariants: invariantsText || "-",
      steps: stepsText || "-",
      corner_cases: cornerCasesText || "-",
      qa_block: qaBlock || "-",
    };
    let rendered = template;
    Object.entries(replacements).forEach(([key, value]) => {
      rendered = rendered.replaceAll(`{{${key}}}`, value);
    });
    return rendered;
  };

  const handleCopyPrompt = async () => {
    setTrainingError(null);
    setPromptCopied(false);
    try {
        const prompt = await buildTrainingPrompt();
        if (!prompt) {
          setTrainingError(toError("Не удалось сформировать промпт.", "BAD_REQUEST"));
          return;
        }
      await navigator.clipboard.writeText(prompt);
      setPromptCopied(true);
      setTimeout(() => setPromptCopied(false), 1600);
    } catch (err) {
      setTrainingError(toError("Не удалось скопировать промпт.", "COPY_FAILED"));
    }
  };

  const handleSaveTraining = async ({ requireGpt } = {}) => {
    setTrainingSaveError(null);
    setTrainingSaveSuccess("");
    if (!trainingCode.trim()) {
      setTrainingSaveError(toError("Введите код для сохранения попытки.", "VALIDATION_ERROR"));
      return;
    }
    let gptPayload = null;
    if (gptJsonInput.trim()) {
      try {
        gptPayload = JSON.parse(gptJsonInput);
      } catch (err) {
        setTrainingSaveError(toError("Некорректный JSON оценки GPT.", "INVALID_JSON_BODY"));
        return;
      }
    } else if (requireGpt) {
      setTrainingSaveError(toError("Вставьте JSON оценки GPT.", "VALIDATION_ERROR"));
      return;
    }

    try {
      setTrainingSaving(true);
      await request("/algorithm-trainings", {
        method: "POST",
        body: JSON.stringify({
          algorithm_id: Number(id),
          code_text: trainingCode,
          gpt_check_result: gptPayload,
        }),
      });
      setTrainingSaveSuccess("Попытка сохранена.");
      await loadTrainings();
    } catch (err) {
      setTrainingSaveError(
        toError(err?.detail || "Не удалось сохранить попытку", err?.code || "UNKNOWN", err?.errors || null)
      );
    } finally {
      setTrainingSaving(false);
    }
  };

  if (loading) {
    return <p className="muted">Загрузка алгоритма...</p>;
  }

  if (error) {
    return <div className="alert error">{error}</div>;
  }

  if (!algorithm) {
    return null;
  }

  return (
    <div className="page-grid">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>{algorithm.title}</h2>
            <p className="muted">Детали алгоритма.</p>
          </div>
          <Link
            className="ghost-button"
            to={`/algorithm-groups/${algorithm.group_id}`}
          >
            К группе
          </Link>
          <button
            className="primary-button"
            type="button"
            onClick={() => setTrainingVisible((prev) => !prev)}
          >
            {trainingVisible ? "Скрыть тренажёр" : "Тренировать"}
          </button>
        </div>

        {sourceInfo && (
          <div className="summary-block">
            <div className="summary-title">Источник</div>
            <div className="summary-value">
              <Link className="ghost-button" to="/books">
                Источник: часть {sourceInfo.partIndex} книги {sourceInfo.bookTitle}
              </Link>
            </div>
          </div>
        )}

        {latestTraining && (
          <div className="summary-block">
            <div className="summary-title">Последняя тренировка</div>
            <div className="summary-value">
              {formatDateTime(latestTraining.created_at)} · Режим{" "}
              {latestTraining.mode === "typing" ? "Печать" : "По памяти"}
              {typeof latestTraining.rating_1_to_5 === "number"
                ? ` · Оценка ${latestTraining.rating_1_to_5}/5`
                : ""}
              {typeof latestTraining.accuracy === "number"
                ? ` · Accuracy ${latestTraining.accuracy}%`
                : ""}
              {typeof latestTraining.duration_sec === "number"
                ? ` · ${latestTraining.duration_sec} сек`
                : ""}
            </div>
            {latestOverall && (
              <div className="summary-text">
                <div>
                  Ключевые пробелы:{" "}
                  {latestOverall.key_gaps?.length
                    ? latestOverall.key_gaps.join(", ")
                    : "Нет."}
                </div>
                <div>
                  Следующие шаги:{" "}
                  {latestOverall.next_steps?.length
                    ? latestOverall.next_steps.join(", ")
                    : "Нет."}
                </div>
                <div>
                  Ограничения:{" "}
                  {latestOverall.limitations?.length
                    ? latestOverall.limitations.join(", ")
                    : "Нет."}
                </div>
                {latestItems.length > 0 && (
                  <div>Ответов проверено: {latestItems.length}.</div>
                )}
              </div>
            )}
            {!latestOverall && (
              <div className="summary-text">JSON оценки не сохранён.</div>
            )}
          </div>
        )}

        <div className="summary-block">
          <div className="summary-title">Статистика тренировок</div>
          <div className="card-grid">
            <div className="card">
              <div className="summary-title">Всего попыток</div>
              <div className="summary-value">{trainingStats.attemptsTotal}</div>
            </div>
            <div className="card">
              <div className="summary-title">Последняя попытка</div>
              <div className="summary-value">{formatDateTime(trainingStats.lastAttemptAt)}</div>
            </div>
            <div className="card">
              <div className="summary-title">Средняя оценка</div>
              <div className="summary-value">
                {trainingStats.avgRating != null ? `${trainingStats.avgRating}/5` : "-"}
              </div>
            </div>
            <div className="card">
              <div className="summary-title">Avg accuracy (typing)</div>
              <div className="summary-value">
                {trainingStats.avgAccuracy != null ? `${trainingStats.avgAccuracy}%` : "-"}
              </div>
            </div>
            <div className="card">
              <div className="summary-title">Best accuracy (typing)</div>
              <div className="summary-value">
                {trainingStats.bestAccuracy != null ? `${trainingStats.bestAccuracy}%` : "-"}
              </div>
            </div>
            <div className="card">
              <div className="summary-title">Суммарное время (typing)</div>
              <div className="summary-value">{trainingStats.totalDurationSec} сек</div>
            </div>
          </div>
        </div>

        <div className="summary-block">
          <div className="panel-header">
            <div>
              <div className="summary-title">История тренировок</div>
              <div className="muted">Показываем до 50 последних попыток.</div>
            </div>
            <div className="form-block">
              <label htmlFor="training-mode-filter">Mode</label>
              <select
                id="training-mode-filter"
                value={attemptModeFilter}
                onChange={(event) => setAttemptModeFilter(event.target.value)}
              >
                <option value="all">all</option>
                <option value="typing">typing</option>
                <option value="memory">memory</option>
              </select>
            </div>
          </div>
          <ErrorBanner error={attemptsError} />
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Date/Time</th>
                  <th>Mode</th>
                  <th>Rating</th>
                  <th>Accuracy</th>
                  <th>Duration</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {attemptsLoading && (
                  <tr>
                    <td colSpan={6}>
                      <div className="admin-skeleton" />
                    </td>
                  </tr>
                )}
                {!attemptsLoading && filteredAttempts.length === 0 && (
                  <tr>
                    <td colSpan={6} className="admin-empty">
                      История тренировок пуста.
                    </td>
                  </tr>
                )}
                {!attemptsLoading &&
                  filteredAttempts.map((attempt) => {
                    const overall = attempt.gpt_check_json?.overall || null;
                    return (
                      <tr key={attempt.id}>
                        <td>{formatDateTime(attempt.created_at)}</td>
                        <td>{attempt.mode}</td>
                        <td>{typeof attempt.rating_1_to_5 === "number" ? `${attempt.rating_1_to_5}/5` : "-"}</td>
                        <td>{typeof attempt.accuracy === "number" ? `${attempt.accuracy}%` : "-"}</td>
                        <td>{typeof attempt.duration_sec === "number" ? `${attempt.duration_sec} сек` : "-"}</td>
                        <td>
                          <details>
                            <summary>Details</summary>
                            {overall ? (
                              <div className="summary-text">
                                <div>Key gaps: {overall.key_gaps?.length ? overall.key_gaps.join(", ") : "-"}</div>
                                <div>Next steps: {overall.next_steps?.length ? overall.next_steps.join(", ") : "-"}</div>
                                <div>Limitations: {overall.limitations?.length ? overall.limitations.join(", ") : "-"}</div>
                              </div>
                            ) : (
                              <div className="summary-text">GPT feedback отсутствует.</div>
                            )}
                            {attempt.gpt_check_json && (
                              <details>
                                <summary>Show raw JSON</summary>
                                <pre className="code-area">
                                  <code>{JSON.stringify(attempt.gpt_check_json, null, 2)}</code>
                                </pre>
                              </details>
                            )}
                          </details>
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        </div>

        <div className="summary-grid">
          <div className="summary-card">
            <div className="summary-title">Сводка</div>
            <div className="summary-text">
              {algorithm.summary || "Сводка не найдена."}
            </div>
          </div>
          <div className="summary-card">
            <div className="summary-title">Когда применять</div>
            <div className="summary-text">
              {algorithm.when_to_use || "-"}
            </div>
          </div>
          <div className="summary-card">
            <div className="summary-title">Сложность</div>
            <div className="summary-text">
              {algorithm.complexity || "-"}
            </div>
          </div>
        </div>

        <div className="summary-grid">
          <div className="summary-card">
            <div className="summary-title">Инварианты</div>
            {algorithm.invariants?.length ? (
              <ul className="summary-list">
                {algorithm.invariants.map((item, index) => (
                  <li key={`${item}-${index}`}>{item}</li>
                ))}
              </ul>
            ) : (
              <div className="summary-text">Нет.</div>
            )}
          </div>
          <div className="summary-card">
            <div className="summary-title">Шаги</div>
            {algorithm.steps?.length ? (
              <ul className="summary-list">
                {algorithm.steps.map((item, index) => (
                  <li key={`${item}-${index}`}>{item}</li>
                ))}
              </ul>
            ) : (
              <div className="summary-text">Нет.</div>
            )}
          </div>
          <div className="summary-card">
            <div className="summary-title">Пограничные случаи</div>
            {algorithm.corner_cases?.length ? (
              <ul className="summary-list">
                {algorithm.corner_cases.map((item, index) => (
                  <li key={`${item}-${index}`}>{item}</li>
                ))}
              </ul>
            ) : (
              <div className="summary-text">Нет.</div>
            )}
          </div>
        </div>

        <div className="summary-block">
          <div className="summary-title">Код</div>
          <div className="list">
            {(algorithm.code_snippets || []).map((snippet) => (
              <div key={snippet.id} className="code-snippet">
                <div className="code-snippet-header">
                  <div>
                    <div className="list-title">
                      {snippet.code_kind} · {snippet.language}
                    </div>
                    <div className="list-meta">
                      {snippet.is_reference ? "Референс" : "Заметка"}
                    </div>
                  </div>
                  <button
                    className="ghost-button"
                    type="button"
                    onClick={() => handleCopy(snippet.id, snippet.code_text)}
                  >
                    {copyState.id === snippet.id
                      ? copyState.message
                      : "Copy"}
                  </button>
                </div>
                <pre className="code-area">
                  <code>{snippet.code_text}</code>
                </pre>
              </div>
            ))}
            {!algorithm.code_snippets?.length && (
              <div className="summary-text">Код отсутствует.</div>
            )}
          </div>
        </div>

        {trainingVisible && (
          <div className="summary-block training-panel">
            <div className="summary-title">Тренировка</div>
            <div className="training-mode-tabs">
              <button
                className={`ghost-button${
                  trainingMode === "memory" ? " active" : ""
                }`}
                type="button"
                onClick={() => setTrainingMode("memory")}
              >
                По памяти
              </button>
              <button
                className={`ghost-button${
                  trainingMode === "typing" ? " active" : ""
                }`}
                type="button"
                onClick={() => setTrainingMode("typing")}
              >
                Печать
              </button>
            </div>

            {trainingMode === "memory" && (
              <>
                <div className="summary-text">
                  Введите код по памяти и сравните с эталоном.
                </div>
                <textarea
                  ref={codeInputRef}
                  className="code-input"
                  rows="10"
                  value={trainingCode}
                  onChange={(event) => setTrainingCode(event.target.value)}
                  onKeyDown={handleCodeKeyDown}
                  placeholder="Введите код или псевдокод"
                />
                <div className="form-actions">
                  <button
                    className="ghost-button"
                    type="button"
                    onClick={handleCompare}
                  >
                    Сравнить с эталоном
                  </button>
                  <button
                    className="ghost-button"
                    type="button"
                    onClick={handleCopyPrompt}
                    disabled={promptLoading}
                  >
                    {promptLoading
                      ? "Формирование..."
                      : promptCopied
                        ? "Промпт скопирован"
                        : "Проверить с GPT"}
                  </button>
                  <button
                    className="ghost-button"
                    type="button"
                    onClick={() => handleSaveTraining({ requireGpt: false })}
                    disabled={trainingSaving}
                  >
                    {trainingSaving ? "Сохранение..." : "Сохранить попытку"}
                  </button>
                </div>
                <ErrorBanner error={trainingError} />
                <ErrorBanner error={trainingSaveError} />
                {trainingSaveSuccess && (
                  <div className="alert success">{trainingSaveSuccess}</div>
                )}

                {showDiff && (
                  <div className="diff-table">
                    <div className="diff-header-row">
                      <div className="diff-header">Ваш код</div>
                      <div className="diff-header">Эталон</div>
                    </div>
                    <div className="diff-body">
                      {trainingDiff.map((row) => (
                        <div
                          key={`diff-${row.index}`}
                          className={`diff-line ${row.type}`}
                        >
                          <div className="diff-cell">
                            <span className="diff-line-number">{row.index}</span>
                            <span className="diff-line-text">
                              {row.left || " "}
                            </span>
                          </div>
                          <div className="diff-cell">
                            <span className="diff-line-number">{row.index}</span>
                            <span className="diff-line-text">
                              {row.right || " "}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="summary-card">
                  <div className="summary-title">JSON оценка GPT</div>
                  <textarea
                    rows="6"
                    className="code-input"
                    value={gptJsonInput}
                    onChange={(event) => setGptJsonInput(event.target.value)}
                    placeholder="Вставьте JSON результата проверки"
                  />
                  <div className="form-actions">
                    <button
                      className="primary-button"
                      type="button"
                      onClick={() => handleSaveTraining({ requireGpt: true })}
                      disabled={trainingSaving}
                    >
                      Сохранить оценку
                    </button>
                  </div>
                </div>
              </>
            )}

            {trainingMode === "typing" && (
              <>
                <div className="summary-text">
                  Печатайте код поверх эталона. Ошибки подсвечиваются сразу.
                </div>
                <div className="typing-metrics">
                  <div>
                    Accuracy: {typingAccuracy}% · Время:{" "}
                    {Math.round(typingElapsed)} сек · Скорость: {typingSpeed} сим/сек
                  </div>
                  <button
                    className="ghost-button"
                    type="button"
                    onClick={resetTyping}
                  >
                    Сбросить
                  </button>
                </div>
                <div className="typing-shadow">
                  <pre className="typing-layer typing-reference" ref={typingBackRef}>
                    {referenceSnippet?.code_text || "Нет эталона"}
                  </pre>
                  <pre className="typing-layer typing-overlay" ref={typingOverlayRef}>
                    {typingDiff.map((item, index) => (
                      <span key={`typing-${index}`} className={item.status}>
                        {item.actual || " "}
                      </span>
                    ))}
                  </pre>
                  <textarea
                    ref={typingRef}
                    className="typing-input"
                    value={typingInput}
                    onChange={handleTypingInput}
                    onKeyDown={handleTypingKeyDown}
                    onScroll={syncTypingScroll}
                    placeholder="Начните печатать здесь"
                  />
                </div>
                <ErrorBanner error={typingSaveError} />
                {typingSaveSuccess && (
                  <div className="alert success">{typingSaveSuccess}</div>
                )}
                <div className="form-actions">
                  <button
                    className="primary-button"
                    type="button"
                    onClick={handleSaveTyping}
                    disabled={trainingSaving}
                  >
                    Сохранить результат
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </section>
    </div>
  );
};

export default AlgorithmDetail;
