import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import './i18n';
import './styles.css';
import { CurrencyProvider } from './components/currency';
import { AuthProvider } from './components/auth';
import { removeLegacySettings } from './components/storage';
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
import { VisitsPage } from './pages/VisitsPage';
import { ConsultPage } from './pages/ConsultPage';
import { BookingsPage } from './pages/BookingsPage';
import { AftercarePage } from './pages/AftercarePage';
import { NotFoundPage } from './pages/NotFoundPage';

// 계정별 저장(이름@계정) 전의 찜·방문 기록 키는 주인을 알 수 없어 지운다
removeLegacySettings();

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
            <Route path="mypage/bookings" element={<RequireLogin><BookingsPage /></RequireLogin>} />
            <Route path="mypage/visits" element={<RequireLogin><VisitsPage /></RequireLogin>} />
            <Route path="mypage/:section" element={<RequireLogin><PlaceholderPage titleKey="nav.mypage" /></RequireLogin>} />
            <Route path="legal/:slug" element={<LegalPage />} />
            {/* 챗봇도 사이트 헤더·메뉴는 그대로, 대화 목록은 챗봇 영역 안에 따로. 로그인한 사람만 (데모 계정 포함, plan-step7 결정 4) */}
            <Route path="chatbot" element={<RequireLogin><ChatbotPage /></RequireLogin>} />
            {/* 상담/예약: 병원별 1:1 상담 (확정은 병원) · 사후관리: 방문 완료 예약별로 그 병원 의료진과 대화 (둘 다 로그인 필요) */}
            <Route path="booking" element={<RequireLogin><ConsultPage /></RequireLogin>} />
            <Route path="aftercare" element={<RequireLogin><AftercarePage /></RequireLogin>} />
            {/* 위에 없는 주소는 빈 화면 대신 "페이지를 찾을 수 없어요" */}
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
      </AuthProvider>
    </CurrencyProvider>
  </StrictMode>,
);
