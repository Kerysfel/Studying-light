import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";

import router from "./router.jsx";
import "./styles.css";
import { applyThemePreference, getThemePreference } from "./theme.js";

const root = document.getElementById("root");

applyThemePreference(getThemePreference());

createRoot(root).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>
);
