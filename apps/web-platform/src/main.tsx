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
import { ChatbotPage } from './pages/ChatbotPage';

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
            <Route path="about" element={<PlaceholderPage titleKey="nav.about" />} />
            <Route path="login" element={<LoginPage />} />
            {/* 마이페이지는 로그인 후에만 */}
            <Route path="mypage" element={<RequireLogin><MyPage /></RequireLogin>} />
            <Route path="mypage/saved" element={<RequireLogin><SavedHospitalsPage /></RequireLogin>} />
            <Route path="mypage/:section" element={<RequireLogin><PlaceholderPage titleKey="nav.mypage" /></RequireLogin>} />
            <Route path="legal/:slug" element={<LegalPage />} />
            {/* 챗봇도 사이트 헤더·메뉴는 그대로, 대화 목록은 챗봇 영역 안에 따로 */}
            <Route path="chatbot" element={<ChatbotPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
      </AuthProvider>
    </CurrencyProvider>
  </StrictMode>,
);
