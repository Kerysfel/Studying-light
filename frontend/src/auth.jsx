import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { request, setApiAuthHandlers } from "./api.js";
import NotFound from "./pages/NotFound.jsx";

const AUTH_TOKEN_STORAGE_KEY = "studying_light_access_token";
const AUTH_LAST_EMAIL_STORAGE_KEY = "studying_light_last_email";

const AuthContext = createContext(null);

const readStorage = (key) => {
  try {
    const value = localStorage.getItem(key);
    return value && value.trim() ? value.trim() : null;
  } catch (error) {
    return null;
  }
};

const saveStorage = (key, value) => {
  try {
    if (value) {
      localStorage.setItem(key, value);
      return;
    }
    localStorage.removeItem(key);
  } catch (error) {
    // Ignore storage write errors and keep in-memory state.
  }
};

const isAuthError = (error) => {
  return error?.code === "AUTH_REQUIRED" || error?.code === "AUTH_INVALID";
};

const isInactiveError = (error) => {
  return error?.code === "ACCOUNT_INACTIVE";
};

const GuardLoader = () => {
  return (
    <div className="content">
      <main className="page">
        <section className="panel">
          <h2>Проверяем доступ</h2>
          <p className="muted">Загружаем профиль пользователя...</p>
        </section>
      </main>
    </div>
  );
};

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(() => readStorage(AUTH_TOKEN_STORAGE_KEY));
  const [me, setMe] = useState(null);
  const [isMeLoading, setIsMeLoading] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [loginNotice, setLoginNotice] = useState(null);

  const clearSession = useCallback(({ notice = null } = {}) => {
    saveStorage(AUTH_TOKEN_STORAGE_KEY, null);
    setToken(null);
    setMe(null);
    setIsMeLoading(false);
    setIsReady(true);
    if (notice) {
      setLoginNotice(notice);
    }
  }, []);

  const logout = useCallback(() => {
    clearSession();
  }, [clearSession]);

  const fetchMe = useCallback(
    async (tokenOverride = null) => {
      const effectiveToken = tokenOverride || token;
      if (!effectiveToken) {
        setMe(null);
        return null;
      }

      setIsMeLoading(true);
      try {
        const profile = await request("/auth/me", {
          headers: {
            Authorization: `Bearer ${effectiveToken}`,
          },
          skipAuthHandling: true,
        });
        setMe(profile);
        saveStorage(AUTH_LAST_EMAIL_STORAGE_KEY, profile.email || null);
        return profile;
      } catch (error) {
        if (isAuthError(error)) {
          clearSession();
          return null;
        }

        if (isInactiveError(error)) {
          clearSession({
            notice: {
              detail: "Account inactive, ask admin to activate",
              code: "ACCOUNT_INACTIVE",
              email: readStorage(AUTH_LAST_EMAIL_STORAGE_KEY),
            },
          });
          return null;
        }

        throw error;
      } finally {
        setIsMeLoading(false);
      }
    },
    [clearSession, token]
  );

  const completeLogin = useCallback(
    async (nextToken) => {
      saveStorage(AUTH_TOKEN_STORAGE_KEY, nextToken);
      setToken(nextToken);
      setLoginNotice(null);
      setIsReady(false);
      const profile = await fetchMe(nextToken);
      setIsReady(true);
      return profile;
    },
    [fetchMe]
  );

  const consumeLoginNotice = useCallback(() => {
    const current = loginNotice;
    if (current) {
      setLoginNotice(null);
    }
    return current;
  }, [loginNotice]);

  useEffect(() => {
    setApiAuthHandlers({
      getAccessToken: () => token,
      onAuthError: () => clearSession(),
    });
    return () => {
      setApiAuthHandlers({
        getAccessToken: () => null,
        onAuthError: () => {},
      });
    };
  }, [clearSession, token]);

  useEffect(() => {
    let cancelled = false;

    if (!token) {
      setMe(null);
      setIsReady(true);
      return () => {
        cancelled = true;
      };
    }

    setIsReady(false);
    fetchMe(token)
      .catch(() => {
        // Keep route behavior deterministic; page can show request errors later.
      })
      .finally(() => {
        if (!cancelled) {
          setIsReady(true);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [fetchMe, token]);

  const value = useMemo(
    () => ({
      token,
      me,
      isReady,
      isMeLoading,
      completeLogin,
      refreshMe: fetchMe,
      logout,
      loginNotice,
      consumeLoginNotice,
    }),
    [completeLogin, consumeLoginNotice, fetchMe, isMeLoading, isReady, loginNotice, logout, me, token]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};

export const PublicOnly = () => {
  const { token, me, isReady } = useAuth();

  if (token && !isReady) {
    return <GuardLoader />;
  }

  if (token && me) {
    if (me.must_change_password) {
      return <Navigate to="/force-change-password" replace />;
    }
    return <Navigate to="/app" replace />;
  }

  return <Outlet />;
};

export const RequireAuth = () => {
  const location = useLocation();
  const { token, me, isReady } = useAuth();

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (!isReady || !me) {
    return <GuardLoader />;
  }

  return <Outlet />;
};

export const MustChangePasswordGuard = () => {
  const location = useLocation();
  const { me } = useAuth();

  if (!me) {
    return <Outlet />;
  }

  const isForceChangeRoute = location.pathname === "/force-change-password";
  if (me.must_change_password && !isForceChangeRoute) {
    return <Navigate to="/force-change-password" replace />;
  }

  if (!me.must_change_password && isForceChangeRoute) {
    return <Navigate to="/app" replace />;
  }

  return <Outlet />;
};

export const RequireAdmin = () => {
  const { me } = useAuth();
  if (!me?.is_admin) {
    return <NotFound />;
  }
  return <Outlet />;
};
