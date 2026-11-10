import { Outlet, useMatch } from 'react-router-dom';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { Footer } from './Footer';

export function Layout() {
  // 챗봇·병원 상담은 화면 높이에 맞춰 입력창을 아래에 붙이므로 푸터를 빼고 높이를 고정
  const chatbot = useMatch('/chatbot');
  const consult = useMatch('/booking');
  const isChat = chatbot || consult;

  return (
    <div className={isChat ? 'app-shell is-chat' : 'app-shell'}>
      <Header />
      <div className="app-body">
        <Sidebar />
        <main className="app-main">
          <Outlet />
        </main>
      </div>
      {!isChat && <Footer />}
    </div>
  );
}
