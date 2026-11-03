import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import './i18n';
import './styles.css';
import { CurrencyProvider } from './components/currency';
import { Layout } from './layout/Layout';
import { MainPage } from './pages/MainPage';
import { HospitalsPage } from './pages/HospitalsPage';
import { HospitalDetailPage } from './pages/HospitalDetailPage';
import { PriceGuidePage } from './pages/PriceGuidePage';
import { PlaceholderPage } from './pages/PlaceholderPage';
import { MyPage } from './pages/MyPage';
import { LegalPage } from './pages/LegalPage';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <CurrencyProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<MainPage />} />
            <Route path="hospitals" element={<HospitalsPage />} />
            <Route path="hospitals/:id" element={<HospitalDetailPage />} />
            <Route path="prices" element={<PriceGuidePage />} />
            <Route path="chatbot" element={<PlaceholderPage titleKey="nav.chatbot" />} />
            <Route path="about" element={<PlaceholderPage titleKey="nav.about" />} />
            <Route path="login" element={<PlaceholderPage titleKey="header.login" />} />
            <Route path="mypage" element={<MyPage />} />
            <Route path="mypage/:section" element={<PlaceholderPage titleKey="nav.mypage" />} />
            <Route path="legal/:slug" element={<LegalPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </CurrencyProvider>
  </StrictMode>,
);
