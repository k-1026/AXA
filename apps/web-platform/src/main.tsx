import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import './i18n';
import './styles.css';
import { CurrencyProvider } from './components/currency';
import { AuthProvider } from './components/auth';
import { Layout } from './layout/Layout';
import { MainPage } from './pages/MainPage';
import { HospitalsPage } from './pages/HospitalsPage';
import { HospitalDetailPage } from './pages/HospitalDetailPage';
import { PriceGuidePage } from './pages/PriceGuidePage';
import { PlaceholderPage } from './pages/PlaceholderPage';
import { MyPage } from './pages/MyPage';
import { SavedHospitalsPage } from './pages/SavedHospitalsPage';
import { LoginPage } from './pages/LoginPage';
import { RequireLogin } from './features/mypage/RequireLogin';
import { LegalPage } from './pages/LegalPage';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <CurrencyProvider>
      <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<MainPage />} />
            <Route path="hospitals" element={<HospitalsPage />} />
            <Route path="hospitals/:id" element={<HospitalDetailPage />} />
            <Route path="prices" element={<PriceGuidePage />} />
            <Route path="chatbot" element={<PlaceholderPage titleKey="nav.chatbot" />} />
            <Route path="about" element={<PlaceholderPage titleKey="nav.about" />} />
            <Route path="login" element={<LoginPage />} />
            {/* 마이페이지는 로그인 후에만 */}
            <Route path="mypage" element={<RequireLogin><MyPage /></RequireLogin>} />
            <Route path="mypage/saved" element={<RequireLogin><SavedHospitalsPage /></RequireLogin>} />
            <Route path="mypage/:section" element={<RequireLogin><PlaceholderPage titleKey="nav.mypage" /></RequireLogin>} />
            <Route path="legal/:slug" element={<LegalPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
      </AuthProvider>
    </CurrencyProvider>
  </StrictMode>,
);
