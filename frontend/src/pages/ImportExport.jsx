import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { getErrorMessage, request } from "../api.js";
import Markdown from "../components/Markdown.jsx";

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

const normalizeTitle = (value) =>
  typeof value === "string" ? value.trim().toLowerCase() : "";

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
  const [algorithmError, setAlgorithmError] = useState(null);
  const [algorithmSuccess, setAlgorithmSuccess] = useState("");
  const [algorithmImportResult, setAlgorithmImportResult] = useState(null);
  const [algorithmImportLoading, setAlgorithmImportLoading] = useState(false);
  const [groupSuggestions, setGroupSuggestions] = useState([]);
  const [groupOptions, setGroupOptions] = useState([]);
  const [groupsLoading, setGroupsLoading] = useState(false);
  const [groupsError, setGroupsError] = useState("");
  const [groupAssignments, setGroupAssignments] = useState({});
  const [bulkGroupId, setBulkGroupId] = useState("");
  const [creatingGroupFor, setCreatingGroupFor] = useState(null);
  const [groupTitle, setGroupTitle] = useState("");
  const [groupDescription, setGroupDescription] = useState("");
  const [groupNotes, setGroupNotes] = useState("");
  const [groupFormError, setGroupFormError] = useState("");
  const groupIdRef = useRef(1);

  const loadGroups = useCallback(
    async ({ preserveNew = true } = {}) => {
      try {
        setGroupsLoading(true);
        setGroupsError("");
        const data = await request("/algorithm-groups");
        const existingGroups = data.map((group) => ({
          id: `existing-${group.id}`,
          source: "existing",
          groupId: group.id,
          title: group.title,
          description: group.description,
          notes: group.notes,
        }));
        setGroupOptions((prev) => {
          if (!preserveNew) {
            return existingGroups;
          }
          const newGroups = prev.filter((item) => item.source === "new");
          return [...existingGroups, ...newGroups];
        });
      } catch (err) {
        setGroupsError(getErrorMessage(err));
      } finally {
        setGroupsLoading(false);
      }
    },
    []
  );

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
    loadGroups();
  }, [loadGroups]);

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

  const groupSelectOptions = useMemo(
    () =>
      groupOptions.map((group) => ({
        value: group.id,
        label:
          group.source === "new" ? `Новая: ${group.title}` : group.title,
      })),
    [groupOptions]
  );

  const groupTitleById = useMemo(() => {
    const map = new Map();
    groupOptions.forEach((group) => {
      if (group.source === "existing") {
        map.set(group.groupId, group.title);
      }
    });
    return map;
  }, [groupOptions]);

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

  const openGroupForm = (target) => {
    const suggested =
      typeof target === "number"
        ? algorithmItems[target]?.suggested_group || ""
        : "";
    setCreatingGroupFor(target);
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
      const algorithmTitle =
        typeof creatingGroupFor === "number"
          ? algorithmItems[creatingGroupFor]?.title || ""
          : "";
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
    const id = `new-${groupIdRef.current}`;
    groupIdRef.current += 1;
    const group = {
      id,
      title,
      description: groupDescription.trim() || null,
      notes: groupNotes.trim() || null,
      source: "new",
    };
    setGroupOptions((prev) => [...prev, group]);
    if (creatingGroupFor === "bulk") {
      setBulkGroupId(id);
      const nextAssignments = {};
      algorithmItems.forEach((_, index) => {
        nextAssignments[index] = id;
      });
      setGroupAssignments(nextAssignments);
    } else if (typeof creatingGroupFor === "number") {
      setGroupAssignments((prev) => ({ ...prev, [creatingGroupFor]: id }));
    }
    setCreatingGroupFor(null);
    resetGroupForm();
  };

  const renderGroupForm = () => (
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
          onChange={(event) => setGroupDescription(event.target.value)}
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
      {groupFormError && <div className="alert error">{groupFormError}</div>}
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
  );

  const handleAlgorithmParse = () => {
    setAlgorithmError(null);
    setAlgorithmSuccess("");
    setAlgorithmImportResult(null);
    setAlgorithmItems([]);
    setGroupSuggestions([]);
    setGroupAssignments({});
    setBulkGroupId("");
    setCreatingGroupFor(null);
    resetGroupForm();

    const raw = algorithmPayload.trim();
    if (!raw) {
      setAlgorithmError({
        message: "Вставьте JSON с алгоритмами.",
        code: null,
        detail: null,
      });
      return;
    }

    let data;
    try {
      data = JSON.parse(raw);
    } catch (err) {
      setAlgorithmError({
        message: "Некорректный JSON для алгоритмов.",
        code: null,
        detail: null,
      });
      return;
    }

    if (!data || typeof data !== "object" || Array.isArray(data)) {
      setAlgorithmError({
        message: "Ожидается JSON-объект с полем algorithms.",
        code: null,
        detail: null,
      });
      return;
    }

    if (!Array.isArray(data.algorithms)) {
      setAlgorithmError({
        message: "Поле algorithms должно быть массивом.",
        code: null,
        detail: null,
      });
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
      setAlgorithmError({
        message: "JSON не содержит алгоритмов для импорта.",
        code: null,
        detail: null,
      });
      return;
    }

    const hasMissingTitle = algorithms.some((item) => !item.title);
    if (hasMissingTitle) {
      setAlgorithmError({
        message: "Каждый алгоритм должен иметь title.",
        code: null,
        detail: null,
      });
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

  const handleAlgorithmImport = async () => {
    setAlgorithmError(null);
    setAlgorithmSuccess("");
    setAlgorithmImportResult(null);
    if (!algorithmItems.length) {
      setAlgorithmError({
        message: "Сначала вставьте и разберите JSON.",
        code: null,
        detail: null,
      });
      return;
    }
    const missing = algorithmItems.filter(
      (_, index) => !groupAssignments[index]
    );
    if (missing.length) {
      setAlgorithmError({
        message: "Выберите группу для каждого алгоритма.",
        code: null,
        detail: null,
      });
      return;
    }

    const groupsById = new Map(
      groupOptions.map((group) => [group.id, group])
    );
    const groupsPayload = new Map();
    let hasInvalidAssignment = false;
    const algorithmsPayload = algorithmItems.map((item, index) => {
      const assignment = groupAssignments[index];
      const group = groupsById.get(assignment);
      if (!group) {
        hasInvalidAssignment = true;
        return null;
      }
      const base = {
        title: item.title,
        summary: item.summary,
        when_to_use: item.when_to_use,
        complexity: item.complexity,
        invariants: item.invariants,
        steps: item.steps,
        corner_cases: item.corner_cases,
        review_questions_by_interval: item.review_questions_by_interval,
        code: item.code,
        suggested_group: item.suggested_group || null,
        source_part_id: item.source_part_id ?? null,
      };

      if (group.source === "existing") {
        return { ...base, group_id: group.groupId };
      }

      const normalized = normalizeTitle(group.title);
      if (!groupsPayload.has(normalized)) {
        groupsPayload.set(normalized, {
          title: group.title,
          description: group.description || null,
          notes: group.notes || null,
        });
      }
      return { ...base, group_title_new: group.title };
    });

    if (hasInvalidAssignment || algorithmsPayload.some((item) => !item)) {
      setAlgorithmError({
        message: "Выбранная группа недоступна. Обновите список.",
        code: null,
        detail: null,
      });
      return;
    }

    const prepared = {
      groups: Array.from(groupsPayload.values()),
      algorithms: algorithmsPayload,
    };

    try {
      setAlgorithmImportLoading(true);
      const response = await request("/algorithms/import", {
        method: "POST",
        body: JSON.stringify(prepared),
      });
      const createdItems = Array.isArray(response.algorithms_created)
        ? response.algorithms_created
        : [];
      const resultItems = createdItems.map((item, index) => ({
        ...item,
        title: algorithmItems[index]?.title || `Алгоритм ${index + 1}`,
      }));
      setAlgorithmImportResult({
        ...response,
        algorithms_created: resultItems,
      });
      setAlgorithmSuccess(
        `Импорт завершен. Алгоритмов: ${resultItems.length}. Повторений: ${
          response.review_items_created || 0
        }.`
      );
      loadGroups({ preserveNew: false });
    } catch (err) {
      setAlgorithmError({
        message: getErrorMessage(err),
        code: err.code || null,
        detail: err.detail || null,
      });
    } finally {
      setAlgorithmImportLoading(false);
    }
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
                <div className="card-detail">
                  <Markdown content={selectedPart.gpt_summary} />
                </div>
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
        {groupsLoading && <p className="muted">Загрузка групп...</p>}
        {groupsError && <div className="alert error">{groupsError}</div>}
        <div className="form-grid">
          <div className="form-block full">
            <label>JSON</label>
            <textarea
              rows="10"
              value={algorithmPayload}
              onChange={(event) => {
                setAlgorithmPayload(event.target.value);
                setAlgorithmError(null);
                setAlgorithmSuccess("");
                setAlgorithmImportResult(null);
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
        {algorithmError && (
          <div className="alert error">
            <div>{algorithmError.message}</div>
            {(algorithmError.detail || algorithmError.code) && (
              <div className="muted">
                {algorithmError.detail && (
                  <span>Детали: {algorithmError.detail}. </span>
                )}
                {algorithmError.code && (
                  <span>Код: {algorithmError.code}.</span>
                )}
              </div>
            )}
          </div>
        )}
        {algorithmSuccess && (
          <div className="alert success">{algorithmSuccess}</div>
        )}
        {algorithmImportResult && (
          <div className="summary-block">
            <div className="summary-title">Результаты импорта</div>
            <div className="summary-value">
              Алгоритмов: {algorithmImportResult.algorithms_created?.length || 0} ·
              Повторений: {algorithmImportResult.review_items_created || 0}
            </div>
            <div className="list">
              {(algorithmImportResult.algorithms_created || []).map((item) => {
                const groupTitle =
                  groupTitleById.get(item.group_id) || `Группа #${item.group_id}`;
                return (
                  <div
                    key={`${item.algorithm_id}-${item.group_id}`}
                    className="list-row"
                  >
                    <div>
                      <div className="list-title">
                        <a
                          href={`/api/v1/algorithms/${item.algorithm_id}`}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {item.title || `Алгоритм #${item.algorithm_id}`}
                        </a>
                      </div>
                      <div className="list-meta">
                        Группа{" "}
                        <a
                          href={`/api/v1/algorithm-groups/${item.group_id}`}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {groupTitle}
                        </a>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
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

            <div className="form-inline">
              <div className="form-block">
                <label>Группа для всех</label>
                <select
                  value={bulkGroupId}
                  onChange={(event) => {
                    const value = event.target.value;
                    if (value === "__new__") {
                      openGroupForm("bulk");
                      setBulkGroupId("");
                      return;
                    }
                    setBulkGroupId(value);
                  }}
                  disabled={groupsLoading}
                >
                  <option value="">Выберите группу</option>
                  {groupSelectOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                  <option value="__new__">+ Создать новую группу</option>
                </select>
              </div>
              <button
                className="ghost-button"
                type="button"
                onClick={handleApplyGroupToAll}
                disabled={!bulkGroupId || groupsLoading}
              >
                Применить ко всем
              </button>
            </div>

            {creatingGroupFor === "bulk" && renderGroupForm()}

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
                        onChange={(event) => {
                          const value = event.target.value;
                          if (value === "__new__") {
                            openGroupForm(index);
                            setGroupAssignments((prev) => ({
                              ...prev,
                              [index]: "",
                            }));
                            return;
                          }
                          setGroupAssignments((prev) => ({
                            ...prev,
                            [index]: value,
                          }));
                        }}
                        disabled={groupsLoading}
                      >
                        <option value="">Выберите группу</option>
                        {groupSelectOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                        <option value="__new__">+ Создать новую группу</option>
                      </select>
                    </div>
                  </div>
                  {creatingGroupFor === index && renderGroupForm()}
                </div>
              ))}
            </div>

            <div className="form-actions">
              <button
                className="primary-button"
                type="button"
                onClick={handleAlgorithmImport}
                disabled={!canImportAlgorithms || algorithmImportLoading || groupsLoading}
              >
                {algorithmImportLoading ? "Импорт..." : "Импортировать"}
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
