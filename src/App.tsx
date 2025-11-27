import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { ToastProvider } from './contexts/ToastContext';
import { ProviderProvider } from './contexts/ProviderContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { ToastContainer } from './components/ToastContainer';
import Layout from './components/Layout';
import Login from './pages/Login';
import Register from './pages/Register';
import GoogleCallback from './pages/GoogleCallback';
import { Chat } from './pages/Chat';
import SearchPage from './pages/SearchPage';
import SettingsPage from './pages/SettingsPage';
import './App.css';

function App() {
  return (
    <ToastProvider>
      <ProviderProvider>
        <AuthProvider>
          <Router>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/auth/google/callback" element={<GoogleCallback />} />
              <Route
                path="/chat"
                element={
                  <ProtectedRoute>
                    <Layout>
                      <Chat />
                    </Layout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/search"
                element={
                  <ProtectedRoute>
                    <Layout>
                      <SearchPage />
                    </Layout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/settings"
                element={
                  <ProtectedRoute>
                    <Layout>
                      <SettingsPage />
                    </Layout>
                  </ProtectedRoute>
                }
              />
              <Route path="/" element={<Navigate to="/chat" replace />} />
              <Route path="*" element={<Navigate to="/chat" replace />} />
            </Routes>
            <ToastContainer />
          </Router>
        </AuthProvider>
      </ProviderProvider>
    </ToastProvider>
  );
}

export default App;
