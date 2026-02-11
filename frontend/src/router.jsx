import { createBrowserRouter } from "react-router-dom";

import AppLayout from "./App.jsx";
import {
  MustChangePasswordGuard,
  PublicOnly,
  RequireAdmin,
  RequireAuth,
} from "./auth.jsx";
import About from "./pages/About.jsx";
import AdminPasswordResets from "./pages/AdminPasswordResets.jsx";
import AdminUsers from "./pages/AdminUsers.jsx";
import AlgorithmDetail from "./pages/AlgorithmDetail.jsx";
import AlgorithmGroupDetail from "./pages/AlgorithmGroupDetail.jsx";
import AlgorithmGroups from "./pages/AlgorithmGroups.jsx";
import Books from "./pages/Books.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import ForceChangePassword from "./pages/ForceChangePassword.jsx";
import ForgotPassword from "./pages/ForgotPassword.jsx";
import ImportExport from "./pages/ImportExport.jsx";
import Landing from "./pages/Landing.jsx";
import Login from "./pages/Login.jsx";
import NotFound from "./pages/NotFound.jsx";
import ReadingSession from "./pages/ReadingSession.jsx";
import Register from "./pages/Register.jsx";
import Reviews from "./pages/Reviews.jsx";
import Settings from "./pages/Settings.jsx";
import Stats from "./pages/Stats.jsx";

const router = createBrowserRouter([
  {
    path: "/",
    children: [
      {
        element: <PublicOnly />,
        children: [
          { index: true, element: <Landing /> },
          { path: "login", element: <Login /> },
          { path: "register", element: <Register /> },
          { path: "forgot-password", element: <ForgotPassword /> },
        ],
      },
      {
        element: <RequireAuth />,
        children: [
          {
            element: <MustChangePasswordGuard />,
            children: [
              { path: "force-change-password", element: <ForceChangePassword /> },
              {
                element: <AppLayout />,
                children: [
                  { path: "app", element: <Dashboard /> },
                  { path: "session", element: <ReadingSession /> },
                  { path: "reviews", element: <Reviews /> },
                  { path: "stats", element: <Stats /> },
                  { path: "books", element: <Books /> },
                  { path: "settings", element: <Settings /> },
                  { path: "import", element: <ImportExport /> },
                  { path: "algorithm-groups", element: <AlgorithmGroups /> },
                  { path: "algorithm-groups/:id", element: <AlgorithmGroupDetail /> },
                  { path: "algorithms/:id", element: <AlgorithmDetail /> },
                  { path: "about", element: <About /> },
                  {
                    element: <RequireAdmin />,
                    children: [
                      { path: "admin/users", element: <AdminUsers /> },
                      { path: "admin/password-resets", element: <AdminPasswordResets /> },
                    ],
                  },
                ],
              },
            ],
          },
        ],
      },
      { path: "*", element: <NotFound /> },
    ],
  },
]);

export default router;
