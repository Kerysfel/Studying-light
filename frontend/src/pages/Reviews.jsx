import { useEffect, useMemo, useState } from "react";

import { getErrorMessage, request, requestText } from "../api.js";

const Reviews = () => {
  const [items, setItems] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [answers, setAnswers] = useState({});
  const [feedback, setFeedback] = useState("");
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [showPrompt, setShowPrompt] = useState(false);
  const [copied, setCopied] = useState(false);
  const [feedbackSaving, setFeedbackSaving] = useState(false);
  const [promptLoading, setPromptLoading] = useState(false);
  const [promptTemplate, setPromptTemplate] = useState("");

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        setLoading(true);
        const data = await request("/reviews/today");
        if (!active) {
          return;
        }
        setItems(data);
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

  const questions = detail?.questions || [];

  const handleStartReview = async (reviewId) => {
    setActionError("");
    setSuccessMessage("");
    setShowPrompt(false);
    setCopied(false);
    if (reviewId === selectedId) {
      return;
    }
    try {
      setDetailLoading(true);
      const data = await request(`/reviews/${reviewId}`);
      setDetail(data);
      setSelectedId(reviewId);
      setFeedback("");
      const nextAnswers = {};
      data.questions.forEach((question, index) => {
        nextAnswers[index] = "";
      });
      setAnswers(nextAnswers);
    } catch (err) {
      setActionError(getErrorMessage(err));
    } finally {
      setDetailLoading(false);
    }
  };

  const handleAnswerChange = (index, value) => {
    setAnswers((prev) => ({ ...prev, [index]: value }));
  };

  const buildAnswerPayload = () => {
    const payload = {};
    questions.forEach((question, index) => {
      payload[question] = answers[index] || "";
    });
    return payload;
  };

  const hasMissingAnswers = useMemo(() => {
    if (!questions.length) {
      return false;
    }
    return questions.some((question, index) => !answers[index]?.trim());
  }, [questions, answers]);

  const buildCheckPrompt = () => {
    if (!promptTemplate || !detail) {
      return "";
    }
    const qaBlock = questions
      .map((question, index) => {
        const answer = answers[index] || "-";
        return `Вопрос: ${question}\nОтвет: ${answer}`;
      })
      .join("\n\n");
    const replacements = {
      book_title: detail.book_title || "-",
      part_index: String(detail.part_index || "-"),
      label: detail.label || "-",
      summary: detail.summary || "-",
      qa_block: qaBlock || "-",
    };
    let rendered = promptTemplate;
    Object.entries(replacements).forEach(([key, value]) => {
      rendered = rendered.replaceAll(`{{${key}}}`, value);
    });
    return rendered;
  };

  const handleCopyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(buildCheckPrompt());
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch (err) {
      setActionError("Не удалось скопировать текст.");
    }
  };

  const openCheckPrompt = async () => {
    if (!detail) {
      setActionError("Выберите повторение.");
      return;
    }
    setCopied(false);
    setActionError("");
    try {
      setPromptLoading(true);
      if (!promptTemplate) {
        const template = await requestText("/prompts/check_answers");
        setPromptTemplate(template);
      }
      setShowPrompt(true);
    } catch (err) {
      setActionError(getErrorMessage(err));
    } finally {
      setPromptLoading(false);
    }
  };

  const handleComplete = async () => {
    if (!detail) {
      return;
    }
    setActionError("");
    setSuccessMessage("");
    if (hasMissingAnswers) {
      setActionError("Ответьте на все вопросы, затем завершите повторение.");
      return;
    }
    try {
      await request(`/reviews/${detail.id}/complete`, {
        method: "POST",
        body: JSON.stringify({ answers: buildAnswerPayload() }),
      });
      setItems((prev) => prev.filter((item) => item.id !== detail.id));
      setDetail(null);
      setSelectedId(null);
      setSuccessMessage("Повторение завершено.");
    } catch (err) {
      setActionError(getErrorMessage(err));
    }
  };

  const handleSaveFeedback = async () => {
    if (!detail) {
      return;
    }
    if (!feedback.trim()) {
      setActionError("Вставьте фидбек перед сохранением.");
      return;
    }
    try {
      setFeedbackSaving(true);
      await request(`/reviews/${detail.id}/save_gpt_feedback`, {
        method: "POST",
        body: JSON.stringify({ gpt_check_result: feedback }),
      });
      setSuccessMessage("Фидбек сохранен.");
    } catch (err) {
      setActionError(getErrorMessage(err));
    } finally {
      setFeedbackSaving(false);
    }
  };

  return (
    <div className="review-layout">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Повторения на сегодня</h2>
            <p className="muted">Сначала закрывайте короткие интервалы.</p>
          </div>
          <span className="badge">Сегодня</span>
        </div>
        {error && <div className="alert error">{error}</div>}
        {loading && <p className="muted">Загрузка повторений...</p>}
        {!loading && items.length === 0 && (
          <div className="empty-state">На сегодня повторений нет.</div>
        )}
        <div className="list">
          {items.map((item) => (
            <div
              key={item.id}
              className={`list-row review-list-item${
                selectedId === item.id ? " active" : ""
              }`}
            >
              <div>
                <div className="list-title">{item.book_title}</div>
                <div className="list-meta">
                  Часть {item.part_index} · Интервал {item.interval_days} дней
                </div>
              </div>
              <button
                className="primary-button"
                type="button"
                onClick={() => handleStartReview(item.id)}
              >
                Начать повторение
              </button>
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Сессия повторения</h2>
            <p className="muted">Сводка и ответы на вопросы.</p>
          </div>
        </div>
        {detailLoading && <p className="muted">Загрузка повторения...</p>}
        {actionError && <div className="alert error">{actionError}</div>}
        {successMessage && <div className="alert success">{successMessage}</div>}
        {!detail && !detailLoading && (
          <div className="empty-state">Выберите повторение в списке.</div>
        )}
        {detail && (
          <div className="review-detail">
            <div className="summary-card">
              <div className="summary-title">Сводка</div>
              <div className="summary-text">
                {detail.summary || "Сводка не найдена."}
              </div>
            </div>

            <div className="questions-block">
              <div className="questions-title">Вопросы</div>
              {questions.length === 0 && (
                <div className="empty-state">Вопросы отсутствуют.</div>
              )}
              {questions.map((question, index) => (
                <div key={question} className="question-card">
                  <div className="question-text">{question}</div>
                  <textarea
                    rows="3"
                    value={answers[index] || ""}
                    onChange={(event) => handleAnswerChange(index, event.target.value)}
                    placeholder="Ваш ответ"
                  />
                </div>
              ))}
            </div>

            <div className="form-actions">
              <button className="ghost-button" type="button" onClick={openCheckPrompt}>
                Сгенерировать промпт проверки
              </button>
              <button className="primary-button" type="button" onClick={handleComplete}>
                Завершить повторение
              </button>
            </div>

            <div className="feedback-block">
              <div className="feedback-title">Фидбек от GPT (опционально)</div>
              <textarea
                rows="4"
                value={feedback}
                onChange={(event) => setFeedback(event.target.value)}
                placeholder="Вставьте результат проверки от GPT"
              />
              <div className="form-actions">
                <button
                  className="ghost-button"
                  type="button"
                  onClick={handleSaveFeedback}
                  disabled={feedbackSaving}
                >
                  {feedbackSaving ? "Сохранение..." : "Сохранить фидбек"}
                </button>
              </div>
            </div>
          </div>
        )}
      </section>

      {showPrompt && detail && (
        <div className="modal-backdrop">
          <div className="modal">
            <div className="modal-header">
              <div>
                <h2>Промпт для проверки</h2>
                <p className="muted">Скопируйте текст и вставьте в GPT.</p>
              </div>
              <button className="ghost-button" type="button" onClick={() => setShowPrompt(false)}>
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
                  value={buildCheckPrompt()}
                  readOnly
                />
              )}
              <div className="modal-actions">
                <button
                  className="primary-button"
                  type="button"
                  onClick={handleCopyPrompt}
                  disabled={promptLoading || !buildCheckPrompt()}
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

export default Reviews;
