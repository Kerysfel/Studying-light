const API_BASE = "/api/v1";

const errorMessages = {
  INVALID_JSON_BODY: "Некорректный JSON. Проверь формат и попробуй снова.",
  VALIDATION_ERROR: "Проверьте введенные данные.",
  IMPORT_PAYLOAD_INVALID: "Некорректные данные импорта. Проверь формат.",
  NOT_FOUND: "Запрашиваемые данные не найдены.",
  BAD_REQUEST: "Запрос сформирован неправильно.",
  CONFLICT: "Конфликт данных. Обновите страницу и попробуйте снова.",
  UNAUTHORIZED: "Нужна авторизация.",
  AUTH_REQUIRED: "Требуется авторизация.",
  AUTH_INVALID: "Сессия истекла. Войдите снова.",
  FORBIDDEN: "Недостаточно прав для действия.",
  INTERNAL_ERROR: "Внутренняя ошибка сервера.",
  NETWORK_ERROR: "Ошибка сети. Проверьте подключение.",
  PAGE_END_INVALID: "Страница остановки не может быть меньше предыдущей.",
};

let authHandlers = {
  getAccessToken: () => null,
  onAuthError: () => {},
};

export const setApiAuthHandlers = (handlers) => {
  authHandlers = {
    ...authHandlers,
    ...(handlers || {}),
  };
};

const parseContentDispositionFilename = (headerValue) => {
  if (!headerValue || typeof headerValue !== "string") {
    return null;
  }

  const filenameStarMatch = headerValue.match(/filename\*\s*=\s*([^;]+)/i);
  if (filenameStarMatch?.[1]) {
    let candidate = filenameStarMatch[1].trim();
    if (candidate.toLowerCase().startsWith("utf-8''")) {
      candidate = candidate.slice(7);
    }
    candidate = candidate.replace(/^"(.*)"$/, "$1");
    try {
      return decodeURIComponent(candidate);
    } catch (error) {
      return candidate;
    }
  }

  const filenameMatch = headerValue.match(/filename\s*=\s*([^;]+)/i);
  if (!filenameMatch?.[1]) {
    return null;
  }
  return filenameMatch[1].trim().replace(/^"(.*)"$/, "$1");
};

const parseJson = async (response) => {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return null;
  }
  return response.json();
};

const asDetailString = (value, fallback = "Ошибка запроса") => {
  if (typeof value === "string" && value.trim()) {
    return value;
  }
  return fallback;
};

const normalizeError = (status, payload) => {
  if (Array.isArray(payload?.detail)) {
    return {
      detail: asDetailString(payload.title, "Проверьте введенные данные."),
      code: payload.code || "VALIDATION_ERROR",
      errors: payload.errors || payload.detail,
    };
  }

  const candidate = payload?.detail && typeof payload.detail === "object" ? payload.detail : payload;

  if (candidate && typeof candidate === "object") {
    return {
      detail: asDetailString(
        candidate.detail,
        asDetailString(payload?.detail, "Ошибка запроса")
      ),
      code: candidate.code || payload?.code || `HTTP_${status}`,
      errors: candidate.errors || payload?.errors || null,
    };
  }

  return {
    detail: asDetailString(payload?.detail, "Ошибка запроса"),
    code: payload?.code || `HTTP_${status}`,
    errors: null,
  };
};

const shouldHandleAuthError = (status, error) => {
  if (status !== 401) {
    return false;
  }

  if (!error?.code) {
    return true;
  }

  return error.code === "AUTH_REQUIRED" || error.code === "AUTH_INVALID" || error.code === "HTTP_401";
};

const buildHeaders = (optionsHeaders = {}, withJson = true) => {
  const headers = {
    ...(withJson ? { "Content-Type": "application/json" } : {}),
    ...optionsHeaders,
  };

  const token = authHandlers.getAccessToken?.();
  if (token && !headers.Authorization) {
    headers.Authorization = `Bearer ${token}`;
  }

  return headers;
};

export const request = async (path, options = {}) => {
  const withJson = !(options.body instanceof FormData);
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: buildHeaders(options.headers, withJson),
    });
  } catch (error) {
    throw { detail: "Ошибка сети", code: "NETWORK_ERROR", errors: null };
  }

  const data = await parseJson(response);
  if (!response.ok) {
    const normalized = normalizeError(response.status, data);
    if (!options.skipAuthHandling && shouldHandleAuthError(response.status, normalized)) {
      authHandlers.onAuthError?.(normalized);
    }
    throw normalized;
  }

  return data;
};

export const downloadFile = async (path, filename) => {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: "GET",
      headers: buildHeaders({}, false),
    });
  } catch (error) {
    throw { detail: "Ошибка сети", code: "NETWORK_ERROR", errors: null };
  }

  if (!response.ok) {
    const data = await parseJson(response);
    const normalized = normalizeError(response.status, data);
    if (shouldHandleAuthError(response.status, normalized)) {
      authHandlers.onAuthError?.(normalized);
    }
    throw normalized;
  }

  const blob = await response.blob();
  const contentDisposition = response.headers.get("content-disposition");
  const filenameFromHeader = parseContentDispositionFilename(contentDisposition);
  const resolvedFilename = filenameFromHeader || filename || "download.bin";
  const objectUrl = URL.createObjectURL(blob);
  try {
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = resolvedFilename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
};

export const requestText = async (path, options = {}) => {
  let response;
  try {
    response = await fetch(path, {
      ...options,
      headers: buildHeaders(options.headers, false),
    });
  } catch (error) {
    throw { detail: "Ошибка сети", code: "NETWORK_ERROR", errors: null };
  }

  const text = await response.text();
  if (!response.ok) {
    let payload = null;
    try {
      payload = JSON.parse(text);
    } catch (error) {
      payload = null;
    }

    const normalized = normalizeError(response.status, payload);
    if (!options.skipAuthHandling && shouldHandleAuthError(response.status, normalized)) {
      authHandlers.onAuthError?.(normalized);
    }
    throw normalized;
  }

  return text;
};

export const getErrorMessage = (error) => {
  if (!error) {
    return "Неизвестная ошибка.";
  }
  const code = error.code || null;
  if (error.detail && code) {
    return `{detail: "${error.detail}", code: "${code}"}`;
  }
  if (code && errorMessages[code]) {
    return `{detail: "${errorMessages[code]}", code: "${code}"}`;
  }
  if (error.detail) {
    return `{detail: "${error.detail}", code: "UNKNOWN"}`;
  }
  return "Неизвестная ошибка.";
};
