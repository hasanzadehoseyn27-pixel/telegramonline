import { Navigate, Route, Routes } from "react-router-dom";
import DashboardLayout from "./components/layout/DashboardLayout";
import Ads from "./pages/Ads";
import SpecialAds from "./pages/SpecialAds";
import ChannelMonitor from "./pages/ChannelMonitor";
import Cheapest from "./pages/Cheapest";
import Channels from "./pages/Channels";
import Alerts from "./pages/Alerts";
import Reports from "./pages/Reports";
import Settings from "./pages/Settings";
import Login from "./pages/Login";
import { isAuthenticated } from "./api/auth.api";

function Protected({ children }: { children: React.ReactNode }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  return <DashboardLayout>{children}</DashboardLayout>;
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <Protected>
            <Ads />
          </Protected>
        }
      />
      <Route
        path="/ads"
        element={
          <Protected>
            <Ads />
          </Protected>
        }
      />
      <Route
        path="/special-ads"
        element={
          <Protected>
            <SpecialAds />
          </Protected>
        }
      />
      <Route
        path="/channel-monitor"
        element={
          <Protected>
            <ChannelMonitor />
          </Protected>
        }
      />
      <Route
        path="/cheapest"
        element={
          <Protected>
            <Cheapest />
          </Protected>
        }
      />
      <Route
        path="/channels"
        element={
          <Protected>
            <Channels />
          </Protected>
        }
      />
      <Route
        path="/alerts"
        element={
          <Protected>
            <Alerts />
          </Protected>
        }
      />
      <Route
        path="/reports"
        element={
          <Protected>
            <Reports />
          </Protected>
        }
      />
      <Route
        path="/settings"
        element={
          <Protected>
            <Settings />
          </Protected>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
