import "@/App.css";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AppLayout } from "@/components/AppLayout";
import DashboardPage from "@/pages/DashboardPage";
import VouchersPage from "@/pages/VouchersPage";
import VlansPage from "@/pages/VlansPage";
import GpioPage from "@/pages/GpioPage";
import ReportsPage from "@/pages/ReportsPage";
import ConfigPage from "@/pages/ConfigPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout />}> 
          <Route index element={<DashboardPage />} />
          <Route path="vouchers" element={<VouchersPage />} />
          <Route path="vlans" element={<VlansPage />} />
          <Route path="gpio" element={<GpioPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="config" element={<ConfigPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
      <Toaster richColors />
    </BrowserRouter>
  );
}

export default App;
