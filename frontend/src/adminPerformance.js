export const PERFORMANCE_SORT_OPTIONS = [
  { value: "last_activity_at", label: "Последняя активность" },
  { value: "reading_sessions", label: "Сессии чтения" },
  { value: "total_activity_count", label: "Всего активностей" },
];

export const SORT_DIRECTION_OPTIONS = [
  { value: "desc", label: "По убыванию" },
  { value: "asc", label: "По возрастанию" },
];

export const ACTIVITY_KIND_OPTIONS = [
  { value: "all", label: "Все" },
  { value: "reading_session", label: "Чтение" },
  { value: "review_theory", label: "Повторение (теория)" },
  { value: "review_algorithm_theory", label: "Повторение (алгоритмы)" },
  { value: "algorithm_training_typing", label: "Тренировка typing" },
  { value: "algorithm_training_memory", label: "Тренировка memory" },
];

const ACTIVITY_KIND_LABELS = ACTIVITY_KIND_OPTIONS.reduce((acc, option) => {
  if (option.value !== "all") {
    acc[option.value] = option.label;
  }
  return acc;
}, {});

const SOURCE_LABELS = {
  live: "Live",
  import: "Import",
  backfill: "Backfill",
};

const STATUS_LABELS = {
  completed: "Completed",
  aborted: "Aborted",
  imported: "Imported",
};

const asNumber = (value) => {
  if (value === null || value === undefined) {
    return null;
  }
  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return null;
  }
  return numeric;
};

export const formatNullable = (value) => {
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  return String(value);
};

export const formatDecimal = (value, digits = 1) => {
  const numeric = asNumber(value);
  if (numeric === null) {
    return "—";
  }
  return numeric.toFixed(digits);
};

export const formatRating = (value) => {
  const numeric = asNumber(value);
  if (numeric === null) {
    return "—";
  }
  return `${numeric.toFixed(1)} / 5`;
};

export const formatScore = (value) => {
  const numeric = asNumber(value);
  if (numeric === null) {
    return "—";
  }
  return `${numeric.toFixed(1)} / 100`;
};

export const formatAccuracy = (value) => {
  const numeric = asNumber(value);
  if (numeric === null) {
    return "—";
  }
  return `${numeric.toFixed(1)}%`;
};

export const formatDuration = (value) => {
  const numeric = asNumber(value);
  if (numeric === null) {
    return "—";
  }

  const total = Math.max(0, Math.round(numeric));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;

  if (hours > 0) {
    return `${hours}ч ${minutes}м`;
  }
  if (minutes > 0) {
    return `${minutes}м ${seconds.toString().padStart(2, "0")}с`;
  }
  return `${seconds}с`;
};

export const formatActivityKind = (value) => {
  return ACTIVITY_KIND_LABELS[value] || value || "—";
};

export const formatActivitySource = (value) => {
  return SOURCE_LABELS[value] || formatNullable(value);
};

export const formatActivityStatus = (value) => {
  return STATUS_LABELS[value] || formatNullable(value);
};

export const buildQueryString = (params) => {
  const query = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {
    if (value === null || value === undefined || value === "") {
      return;
    }
    if (key === "activity_kind" && value === "all") {
      return;
    }
    query.set(key, String(value));
  });

  return query.toString();
};

export const parseInteger = (value, fallback) => {
  const parsed = Number.parseInt(value || "", 10);
  if (Number.isNaN(parsed) || parsed < 0) {
    return fallback;
  }
  return parsed;
};

export const buildEntityPresentation = (event) => {
  if (!event || typeof event !== "object") {
    return { primary: "—", secondary: null };
  }

  let primary = null;
  if (event.algorithm_title) {
    primary = event.algorithm_title;
  } else if (event.book_title) {
    primary = event.book_title;
  } else if (event.algorithm_id !== null && event.algorithm_id !== undefined) {
    primary = `Алгоритм #${event.algorithm_id}`;
  } else if (event.book_id !== null && event.book_id !== undefined) {
    primary = `Книга #${event.book_id}`;
  } else if (
    event.reading_part_id !== null &&
    event.reading_part_id !== undefined
  ) {
    primary = `Часть #${event.reading_part_id}`;
  } else {
    primary = "—";
  }

  const secondary = [];
  if (event.reading_part_label) {
    secondary.push(`Часть: ${event.reading_part_label}`);
  } else if (
    event.reading_part_index !== null &&
    event.reading_part_index !== undefined
  ) {
    secondary.push(`Часть #${event.reading_part_index}`);
  } else if (
    event.reading_part_id !== null &&
    event.reading_part_id !== undefined
  ) {
    secondary.push(`part:${event.reading_part_id}`);
  }
  if (event.review_item_id !== null && event.review_item_id !== undefined) {
    secondary.push(`review:${event.review_item_id}`);
  }
  if (
    event.algorithm_review_item_id !== null &&
    event.algorithm_review_item_id !== undefined
  ) {
    secondary.push(`algo-review:${event.algorithm_review_item_id}`);
  }
  if (
    event.algorithm_training_attempt_id !== null &&
    event.algorithm_training_attempt_id !== undefined
  ) {
    secondary.push(`attempt:${event.algorithm_training_attempt_id}`);
  }

  return {
    primary,
    secondary: secondary.length ? secondary.join(" · ") : null,
  };
};

export const toIsoDate = (value) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toISOString().slice(0, 10);
};

export const dateDaysAgo = (days) => {
  const value = new Date();
  value.setUTCDate(value.getUTCDate() - days);
  return toIsoDate(value);
};
