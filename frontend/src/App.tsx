import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/layout/Sidebar';
import Dashboard from './pages/Dashboard';
import LoadData from './pages/LoadData';
import VariantExplorer from './pages/VariantExplorer';
import VariantAnalysis from './pages/VariantAnalysis';
import Pharmacogenomics from './pages/Pharmacogenomics';
import DiseaseRisk from './pages/DiseaseRisk';
import Settings from './pages/Settings';

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-gray-50">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/files" element={<LoadData />} />
            <Route path="/variants" element={<VariantExplorer />} />
            <Route path="/analysis" element={<VariantAnalysis />} />
            <Route path="/analysis/:variantId" element={<VariantAnalysis />} />
            <Route path="/pharmacogenomics" element={<Pharmacogenomics />} />
            <Route path="/disease-risk" element={<DiseaseRisk />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
