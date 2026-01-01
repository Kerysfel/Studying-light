import { createBrowserRouter } from "react-router-dom";

import AppLayout from "./App.jsx";
import About from "./pages/About.jsx";
import Books from "./pages/Books.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import ImportExport from "./pages/ImportExport.jsx";
import ReadingSession from "./pages/ReadingSession.jsx";
import Reviews from "./pages/Reviews.jsx";
import Settings from "./pages/Settings.jsx";
import NotFound from "./pages/NotFound.jsx";

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: "session", element: <ReadingSession /> },
      { path: "reviews", element: <Reviews /> },
      { path: "books", element: <Books /> },
      { path: "settings", element: <Settings /> },
      { path: "import", element: <ImportExport /> },
      { path: "about", element: <About /> },
      { path: "*", element: <NotFound /> },
    ],
  },
]);

export default router;
