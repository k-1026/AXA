import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import './i18n';
import './styles.css';
import { CurrencyProvider } from './components/currency';
import { Layout } from './layout/Layout';
import { MainPage } from './pages/MainPage';
import { PlaceholderPage } from './pages/PlaceholderPage';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <CurrencyProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<MainPage />} />
            <Route path="hospitals" element={<PlaceholderPage titleKey="nav.hospitals" />} />
            <Route path="prices" element={<PlaceholderPage titleKey="nav.prices" />} />
            <Route path="chatbot" element={<PlaceholderPage titleKey="nav.chatbot" />} />
            <Route path="about" element={<PlaceholderPage titleKey="nav.about" />} />
            <Route path="login" element={<PlaceholderPage titleKey="header.login" />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </CurrencyProvider>
  </StrictMode>,
);
