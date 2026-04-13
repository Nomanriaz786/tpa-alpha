import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import type { ReactNode } from 'react'
import LoginPage from './pages/Login.tsx'
import DashboardPage from './pages/Dashboard.tsx'
import SubscribersPage from './pages/Subscribers.tsx'
import AffiliatesPage from './pages/Affiliates.tsx'
import SettingsPage from './pages/Settings.tsx'
import PaymentPage from './pages/PaymentPage.tsx'

function ProtectedRoute({ children }: { children: ReactNode }) {
  const token = localStorage.getItem('admin_token')
  const expiresAt = localStorage.getItem('token_expires_at')
  
  if (!token || !expiresAt || new Date(expiresAt) < new Date()) {
    return <Navigate to="/login" replace />
  }
  
  return <>{children}</>
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/subscribe" element={<PaymentPage />} />
        
        {/* Protected Routes */}
        <Route 
          path="/" 
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/dashboard" 
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/subscribers" 
          element={
            <ProtectedRoute>
              <SubscribersPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/affiliates" 
          element={
            <ProtectedRoute>
              <AffiliatesPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/settings" 
          element={
            <ProtectedRoute>
              <SettingsPage />
            </ProtectedRoute>
          } 
        />
        
        {/* Catch all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
