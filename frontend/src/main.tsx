import { createRoot } from 'react-dom/client';
import App from './App';
import { AuthProvider } from './auth';
import './styles.css';
import { ToastProvider } from './ui';

createRoot(document.getElementById('root')!).render(
  <AuthProvider>
    <ToastProvider>
      <App />
    </ToastProvider>
  </AuthProvider>,
);
