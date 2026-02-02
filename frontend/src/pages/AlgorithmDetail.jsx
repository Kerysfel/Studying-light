import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getErrorMessage, request, requestText } from "../api.js";

const AlgorithmDetail = () => {
  const { id } = useParams();
  const [algorithm, setAlgorithm] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copyState, setCopyState] = useState({ id: null, message: "" });
  const [bookTitles, setBookTitles] = useState(new Map());
  const [trainingVisible, setTrainingVisible] = useState(false);
  const [trainingCode, setTrainingCode] = useState("");
  const [trainingDiff, setTrainingDiff] = useState([]);
  const [showDiff, setShowDiff] = useState(false);
  const [trainingError, setTrainingError] = useState("");
  const [promptTemplate, setPromptTemplate] = useState("");
  const [promptLoading, setPromptLoading] = useState(false);
  const [promptCopied, setPromptCopied] = useState(false);
  const [gptJsonInput, setGptJsonInput] = useState("");
  const [trainingSaving, setTrainingSaving] = useState(false);
  const [trainingSaveError, setTrainingSaveError] = useState("");
  const [trainingSaveSuccess, setTrainingSaveSuccess] = useState("");
  const [latestTraining, setLatestTraining] = useState(null);
  const codeInputRef = useRef(null);

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
      const data = await request(`/algorithm-trainings?algorithm_id=${id}`);
      setLatestTraining(data[0] || null);
    } catch (err) {
      setLatestTraining(null);
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

  const latestGpt = latestTraining?.gpt_check_json || null;
  const latestOverall = latestGpt?.overall || null;
  const latestItems = Array.isArray(latestGpt?.items) ? latestGpt.items : [];

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

  const handleCompare = () => {
    setTrainingError("");
    if (!referenceSnippet?.code_text) {
      setTrainingError("Нет эталонного кода для сравнения.");
      return;
    }
    if (!trainingCode.trim()) {
      setTrainingError("Введите код для сравнения.");
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
    setTrainingError("");
    setPromptCopied(false);
    try {
      const prompt = await buildTrainingPrompt();
      if (!prompt) {
        setTrainingError("Не удалось сформировать промпт.");
        return;
      }
      await navigator.clipboard.writeText(prompt);
      setPromptCopied(true);
      setTimeout(() => setPromptCopied(false), 1600);
    } catch (err) {
      setTrainingError("Не удалось скопировать промпт.");
    }
  };

  const handleSaveTraining = async ({ requireGpt } = {}) => {
    setTrainingSaveError("");
    setTrainingSaveSuccess("");
    if (!trainingCode.trim()) {
      setTrainingSaveError("Введите код для сохранения попытки.");
      return;
    }
    let gptPayload = null;
    if (gptJsonInput.trim()) {
      try {
        gptPayload = JSON.parse(gptJsonInput);
      } catch (err) {
        setTrainingSaveError("Некорректный JSON оценки GPT.");
        return;
      }
    } else if (requireGpt) {
      setTrainingSaveError("Вставьте JSON оценки GPT.");
      return;
    }

    try {
      setTrainingSaving(true);
      const response = await request("/algorithm-trainings", {
        method: "POST",
        body: JSON.stringify({
          algorithm_id: Number(id),
          code_text: trainingCode,
          gpt_check_result: gptPayload,
        }),
      });
      setTrainingSaveSuccess("Попытка сохранена.");
      setLatestTraining(response);
      await loadTrainings();
    } catch (err) {
      setTrainingSaveError(getErrorMessage(err));
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
              {formatDateTime(latestTraining.created_at)}
              {typeof latestTraining.rating_1_to_5 === "number"
                ? ` · Оценка ${latestTraining.rating_1_to_5}/5`
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
            <div className="summary-title">Тренировка по памяти</div>
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
            {trainingError && <div className="alert error">{trainingError}</div>}
            {trainingSaveError && (
              <div className="alert error">{trainingSaveError}</div>
            )}
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
          </div>
        )}
      </section>
    </div>
  );
};

export default AlgorithmDetail;
