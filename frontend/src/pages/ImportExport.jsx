import { useEffect, useMemo, useRef, useState } from "react";

import { getErrorMessage, request } from "../api.js";

const summarize = (text) => {
  if (!text) {
    return "Краткое содержание недоступно.";
  }
  const words = text.trim().split(/\s+/).slice(0, 10);
  return words.join(" ") + (words.length === 10 ? "..." : "");
};

const formatDate = (value) => {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString();
};

const ImportExport = () => {
  const [books, setBooks] = useState([]);
  const [parts, setParts] = useState([]);
  const [selectedBookId, setSelectedBookId] = useState("");
  const [selectedPartId, setSelectedPartId] = useState("");
  const [payload, setPayload] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingParts, setLoadingParts] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [algorithmPayload, setAlgorithmPayload] = useState("");
  const [algorithmItems, setAlgorithmItems] = useState([]);
  const [algorithmError, setAlgorithmError] = useState("");
  const [algorithmSuccess, setAlgorithmSuccess] = useState("");
  const [groupSuggestions, setGroupSuggestions] = useState([]);
  const [groupOptions, setGroupOptions] = useState([]);
  const [groupAssignments, setGroupAssignments] = useState({});
  const [bulkGroupId, setBulkGroupId] = useState("");
  const [creatingGroupFor, setCreatingGroupFor] = useState(null);
  const [groupTitle, setGroupTitle] = useState("");
  const [groupDescription, setGroupDescription] = useState("");
  const [groupNotes, setGroupNotes] = useState("");
  const [groupFormError, setGroupFormError] = useState("");
  const groupIdRef = useRef(1);

  useEffect(() => {
    let active = true;
    const loadBooks = async () => {
      try {
        const data = await request("/books");
        if (!active) {
          return;
        }
        setBooks(data);
      } catch (err) {
        if (!active) {
          return;
        }
        setError(getErrorMessage(err));
      }
    };
    loadBooks();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    const loadParts = async () => {
      if (!selectedBookId) {
        setParts([]);
        setSelectedPartId("");
        return;
      }
      try {
        setLoadingParts(true);
        const data = await request(`/parts?book_id=${selectedBookId}`);
        if (!active) {
          return;
        }
        setParts(data);
        setError("");
        const stored = localStorage.getItem("lastPartId");
        if (stored && data.some((item) => String(item.id) === stored)) {
          setSelectedPartId(stored);
        }
      } catch (err) {
        if (!active) {
          return;
        }
        setError(getErrorMessage(err));
      } finally {
        if (active) {
          setLoadingParts(false);
        }
      }
    };
    loadParts();
    return () => {
      active = false;
    };
  }, [selectedBookId]);

  useEffect(() => {
    if (selectedPartId) {
      localStorage.setItem("lastPartId", selectedPartId);
    }
  }, [selectedPartId]);

  const selectedPart = useMemo(
    () => parts.find((item) => String(item.id) === selectedPartId) || null,
    [parts, selectedPartId]
  );

  const handleImport = async () => {
    setError("");
    setSuccess("");
    if (!selectedBookId) {
      setError("Сначала выберите книгу.");
      return;
    }
    if (!selectedPartId) {
      setError("Выберите часть для импорта.");
      return;
    }
    if (!payload.trim()) {
      setError("Вставьте JSON для импорта.");
      return;
    }

    let data;
    try {
      data = JSON.parse(payload);
    } catch (err) {
      setError("Некорректный JSON. Проверьте формат.");
      return;
    }

    try {
      setLoading(true);
      const response = await request(`/parts/${selectedPartId}/import_gpt`, {
        method: "POST",
        body: JSON.stringify(data),
      });
      const count = response.review_items?.length || 0;
      setSuccess(`Импорт завершен. Создано повторений: ${count}.`);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const resetGroupForm = () => {
    setGroupTitle("");
    setGroupDescription("");
    setGroupNotes("");
    setGroupFormError("");
  };

  const openGroupForm = (index) => {
    const suggested = algorithmItems[index]?.suggested_group || "";
    setCreatingGroupFor(index);
    setGroupTitle(suggested);
    setGroupDescription("");
    setGroupNotes("");
    setGroupFormError("");
  };

  const handleGenerateGroupNotes = () => {
    const title = groupTitle.trim();
    if (!title) {
      setGroupFormError("Введите название группы.");
      return;
    }
    setGroupFormError("");
    if (!groupDescription.trim()) {
      setGroupDescription(`Группа алгоритмов: ${title}.`);
    }
    if (!groupNotes.trim()) {
      const algorithmTitle = algorithmItems[creatingGroupFor]?.title || "";
      const base = algorithmTitle ? `Алгоритмы: ${algorithmTitle}.` : "";
      setGroupNotes(base || "Формулы/инварианты структуры: ");
    }
  };

  const handleCreateGroup = () => {
    const title = groupTitle.trim();
    if (!title) {
      setGroupFormError("Введите название группы.");
      return;
    }
    const id = `group-${groupIdRef.current}`;
    groupIdRef.current += 1;
    const group = {
      id,
      title,
      description: groupDescription.trim() || null,
      notes: groupNotes.trim() || null,
    };
    setGroupOptions((prev) => [...prev, group]);
    setGroupAssignments((prev) => ({ ...prev, [creatingGroupFor]: id }));
    setCreatingGroupFor(null);
    resetGroupForm();
  };

  const handleAlgorithmParse = () => {
    setAlgorithmError("");
    setAlgorithmSuccess("");
    setAlgorithmItems([]);
    setGroupSuggestions([]);
    setGroupAssignments({});
    setBulkGroupId("");
    setCreatingGroupFor(null);
    resetGroupForm();

    const raw = algorithmPayload.trim();
    if (!raw) {
      setAlgorithmError("Вставьте JSON с алгоритмами.");
      return;
    }

    let data;
    try {
      data = JSON.parse(raw);
    } catch (err) {
      setAlgorithmError("Некорректный JSON для алгоритмов.");
      return;
    }

    if (!data || typeof data !== "object" || Array.isArray(data)) {
      setAlgorithmError("Ожидается JSON-объект с полем algorithms.");
      return;
    }

    if (!Array.isArray(data.algorithms)) {
      setAlgorithmError("Поле algorithms должно быть массивом.");
      return;
    }

    const algorithms = data.algorithms
      .filter((item) => item && typeof item === "object" && !Array.isArray(item))
      .map((item) => ({
        ...item,
        title: typeof item.title === "string" ? item.title.trim() : "",
        summary: typeof item.summary === "string" ? item.summary.trim() : "",
        complexity:
          typeof item.complexity === "string" ? item.complexity.trim() : "",
        suggested_group:
          typeof item.suggested_group === "string"
            ? item.suggested_group.trim()
            : "",
      }));

    if (!algorithms.length) {
      setAlgorithmError("JSON не содержит алгоритмов для импорта.");
      return;
    }

    const hasMissingTitle = algorithms.some((item) => !item.title);
    if (hasMissingTitle) {
      setAlgorithmError("Каждый алгоритм должен иметь title.");
      return;
    }

    const suggestionSet = new Set();
    if (Array.isArray(data.group_suggestions)) {
      data.group_suggestions.forEach((value) => {
        if (typeof value === "string" && value.trim()) {
          suggestionSet.add(value.trim());
        }
      });
    }
    algorithms.forEach((item) => {
      if (item.suggested_group) {
        suggestionSet.add(item.suggested_group);
      }
    });

    setGroupSuggestions(Array.from(suggestionSet));
    setAlgorithmItems(algorithms);
  };

  const handleApplyGroupToAll = () => {
    if (!bulkGroupId) {
      return;
    }
    const nextAssignments = {};
    algorithmItems.forEach((_, index) => {
      nextAssignments[index] = bulkGroupId;
    });
    setGroupAssignments(nextAssignments);
  };

  const handleAlgorithmImport = () => {
    setAlgorithmError("");
    setAlgorithmSuccess("");
    if (!algorithmItems.length) {
      setAlgorithmError("Сначала вставьте и разберите JSON.");
      return;
    }
    const missing = algorithmItems.filter(
      (_, index) => !groupAssignments[index]
    );
    if (missing.length) {
      setAlgorithmError("Выберите группу для каждого алгоритма.");
      return;
    }
    const groupsById = new Map(
      groupOptions.map((group) => [group.id, group])
    );
    const prepared = {
      groups: groupOptions,
      algorithms: algorithmItems.map((item, index) => ({
        ...item,
        group_id: groupAssignments[index],
        group_title: groupsById.get(groupAssignments[index])?.title || null,
      })),
    };
    localStorage.setItem("algorithmImportDraft", JSON.stringify(prepared));
    setAlgorithmSuccess(
      `Импорт подготовлен. Алгоритмов: ${algorithmItems.length}.`
    );
  };

  const canImportAlgorithms = useMemo(
    () => algorithmItems.length > 0,
    [algorithmItems]
  );

  return (
    <div className="page-grid">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Импорт JSON</h2>
            <p className="muted">Вставьте ответ от ChatGPT.</p>
          </div>
        </div>
        <div className="form-grid">
          <div className="form-block">
            <label>Книга</label>
            <select
              value={selectedBookId}
              onChange={(event) => setSelectedBookId(event.target.value)}
            >
              <option value="">Выберите книгу</option>
              {books.map((book) => (
                <option key={book.id} value={book.id}>
                  {book.title}
                </option>
              ))}
            </select>
          </div>
          <div className="form-block">
            <label>Часть</label>
            <select
              value={selectedPartId}
              onChange={(event) => setSelectedPartId(event.target.value)}
              disabled={!selectedBookId || loadingParts}
            >
              <option value="">Выберите часть</option>
              {parts.map((part) => (
                <option key={part.id} value={part.id}>
                  Часть {part.part_index} - {formatDate(part.created_at)}
                </option>
              ))}
            </select>
          </div>
          {selectedPart && (
            <div className="form-block full">
              <label>Детали выбранной части</label>
              <div className="card">
                <div className="card-title">
                  Часть {selectedPart.part_index}
                </div>
                <div className="card-meta">
                  Создано: {formatDate(selectedPart.created_at)}
                </div>
                <div className="card-detail">{summarize(selectedPart.gpt_summary)}</div>
              </div>
            </div>
          )}
          <div className="form-block full">
            <label>JSON</label>
            <textarea
              rows="8"
              value={payload}
              onChange={(event) => setPayload(event.target.value)}
              placeholder='{"gpt_summary": "...", "gpt_questions_by_interval": {...}}'
            />
          </div>
        </div>
        {error && <div className="alert error">{error}</div>}
        {success && <div className="alert success">{success}</div>}
        <div className="form-actions">
          <button
            className="primary-button"
            type="button"
            onClick={handleImport}
            disabled={loading}
          >
            {loading ? "Импорт..." : "Импортировать"}
          </button>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Импорт алгоритмов</h2>
            <p className="muted">
              Вставьте JSON из промпта алгоритмов и распределите по группам.
            </p>
          </div>
        </div>
        <div className="form-grid">
          <div className="form-block full">
            <label>JSON</label>
            <textarea
              rows="10"
              value={algorithmPayload}
              onChange={(event) => {
                setAlgorithmPayload(event.target.value);
                setAlgorithmError("");
                setAlgorithmSuccess("");
              }}
              onBlur={handleAlgorithmParse}
              placeholder='{"group_suggestions": [], "algorithms": [...]}'
            />
          </div>
        </div>
        <div className="form-actions">
          <button
            className="ghost-button"
            type="button"
            onClick={handleAlgorithmParse}
          >
            Разобрать JSON
          </button>
        </div>
        {algorithmError && <div className="alert error">{algorithmError}</div>}
        {algorithmSuccess && (
          <div className="alert success">{algorithmSuccess}</div>
        )}

        {algorithmItems.length > 0 && (
          <>
            <div className="summary-block">
              <div className="summary-title">Найдено</div>
              <div className="summary-value">
                Алгоритмов: {algorithmItems.length}
              </div>
            </div>

            {groupSuggestions.length > 0 && (
              <div className="summary-block">
                <div className="summary-title">Предложения групп</div>
                <div className="pill-row">
                  {groupSuggestions.map((item) => (
                    <span className="pill" key={item}>
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {groupOptions.length > 0 && (
              <div className="form-inline">
                <div className="form-block">
                  <label>Группа для всех</label>
                  <select
                    value={bulkGroupId}
                    onChange={(event) => setBulkGroupId(event.target.value)}
                  >
                    <option value="">Выберите группу</option>
                    {groupOptions.map((group) => (
                      <option key={group.id} value={group.id}>
                        {group.title}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  className="ghost-button"
                  type="button"
                  onClick={handleApplyGroupToAll}
                  disabled={!bulkGroupId}
                >
                  Применить ко всем
                </button>
              </div>
            )}

            <div className="list">
              {algorithmItems.map((item, index) => (
                <div className="card algorithm-card" key={`${item.title}-${index}`}>
                  <div className="algorithm-header">
                    <div>
                      <div className="card-title">{item.title}</div>
                      {item.summary && (
                        <div className="card-meta">{item.summary}</div>
                      )}
                    </div>
                    {item.complexity && (
                      <span className="pill">{item.complexity}</span>
                    )}
                  </div>
                  {item.suggested_group && (
                    <div className="algorithm-meta">
                      Предложенная группа: {item.suggested_group}
                    </div>
                  )}
                  <div className="form-inline">
                    <div className="form-block">
                      <label>Группа</label>
                      <select
                        value={groupAssignments[index] || ""}
                        onChange={(event) =>
                          setGroupAssignments((prev) => ({
                            ...prev,
                            [index]: event.target.value,
                          }))
                        }
                      >
                        <option value="">Выберите группу</option>
                        {groupOptions.map((group) => (
                          <option key={group.id} value={group.id}>
                            {group.title}
                          </option>
                        ))}
                      </select>
                    </div>
                    <button
                      className="ghost-button"
                      type="button"
                      onClick={() => openGroupForm(index)}
                    >
                      Создать новую группу
                    </button>
                  </div>
                  {creatingGroupFor === index && (
                    <div className="summary-card group-form">
                      <div className="form-block">
                        <label>Название группы</label>
                        <input
                          value={groupTitle}
                          onChange={(event) => setGroupTitle(event.target.value)}
                          placeholder="Например, D-куча"
                        />
                      </div>
                      <div className="form-block">
                        <label>Описание (опционально)</label>
                        <textarea
                          rows="3"
                          value={groupDescription}
                          onChange={(event) =>
                            setGroupDescription(event.target.value)
                          }
                          placeholder="Коротко о структуре данных"
                        />
                      </div>
                      <div className="form-block">
                        <label>Формулы/инварианты структуры (опционально)</label>
                        <textarea
                          rows="3"
                          value={groupNotes}
                          onChange={(event) => setGroupNotes(event.target.value)}
                          placeholder="Формулы, инварианты, базовые свойства"
                        />
                      </div>
                      {groupFormError && (
                        <div className="alert error">{groupFormError}</div>
                      )}
                      <div className="form-actions">
                        <button
                          className="ghost-button"
                          type="button"
                          onClick={handleGenerateGroupNotes}
                        >
                          Сгенерировать справку
                        </button>
                        <button
                          className="ghost-button"
                          type="button"
                          onClick={() => setCreatingGroupFor(null)}
                        >
                          Отмена
                        </button>
                        <button
                          className="primary-button"
                          type="button"
                          onClick={handleCreateGroup}
                        >
                          Создать группу
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="form-actions">
              <button
                className="primary-button"
                type="button"
                onClick={handleAlgorithmImport}
                disabled={!canImportAlgorithms}
              >
                Импортировать
              </button>
            </div>
          </>
        )}
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h2>Экспорт</h2>
            <p className="muted">Скачайте данные в формате JSON.</p>
          </div>
        </div>
        <button className="ghost-button" type="button">
          Экспорт JSON
        </button>
      </section>
    </div>
  );
};

export default ImportExport;
