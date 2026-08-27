import React, { useEffect, Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import { fetchMe } from './store/slices/authSlice';

import Navbar          from './components/common/Navbar';
import Footer          from './components/common/Footer';
import ProtectedRoute  from './components/common/ProtectedRoute';
import OnboardingModal from './components/profile/OnboardingModal';
import PageLoader, { RouteProgress } from './components/ui/PageLoader';

// Lazy-loaded pages — code-split per route; PageLoader shows while a chunk loads
const HomePage            = lazy(() => import('./pages/HomePage'));
const LoginPage           = lazy(() => import('./pages/LoginPage'));
const RegisterPage        = lazy(() => import('./pages/RegisterPage'));
const SearchPage          = lazy(() => import('./pages/SearchPage'));
const PropertyDetailPage  = lazy(() => import('./pages/PropertyDetailPage'));
const RecommendationsPage = lazy(() => import('./pages/RecommendationsPage'));
const WishlistPage        = lazy(() => import('./pages/WishlistPage'));
const PredictPricePage    = lazy(() => import('./pages/PredictPricePage'));
const ChatbotPage         = lazy(() => import('./pages/ChatbotPage'));
const ProfilePage         = lazy(() => import('./pages/ProfilePage'));
const AddPropertyPage     = lazy(() => import('./pages/AddPropertyPage'));
const AdminDashboardPage  = lazy(() => import('./pages/AdminDashboardPage'));
const SafetyDashboardPage = lazy(() => import('./pages/SafetyDashboardPage'));

export default function App() {
  const dispatch = useDispatch();
  const token    = useSelector((s) => s.auth.token);

  useEffect(() => {
    if (token) dispatch(fetchMe());
  }, [token, dispatch]);

  return (
    <BrowserRouter>
      <RouteProgress />
      <div className="flex flex-col min-h-screen">
        <Navbar />
        <main className="flex-1">
          <Suspense fallback={<PageLoader />}>
            <Routes>
              <Route path="/"               element={<HomePage />} />
              <Route path="/login"          element={<LoginPage />} />
              <Route path="/register"       element={<RegisterPage />} />
              <Route path="/search"         element={<SearchPage />} />
              <Route path="/property/:id"   element={<PropertyDetailPage />} />
              <Route path="/predict-price"  element={<PredictPricePage />} />
              <Route path="/chatbot"        element={<ChatbotPage />} />
              <Route path="/safety"         element={<SafetyDashboardPage />} />

              {/* Protected routes */}
              <Route path="/recommendations" element={<ProtectedRoute><RecommendationsPage /></ProtectedRoute>} />
              <Route path="/wishlist"         element={<ProtectedRoute><WishlistPage /></ProtectedRoute>} />
              <Route path="/profile"          element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
              <Route path="/add-property"     element={<ProtectedRoute roles={['landlord','admin']}><AddPropertyPage /></ProtectedRoute>} />
              <Route path="/admin"            element={<ProtectedRoute roles={['admin']}><AdminDashboardPage /></ProtectedRoute>} />

              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </main>
        <Footer />
      </div>
      <OnboardingModal />
      <ToastContainer position="top-right" autoClose={3000} />
    </BrowserRouter>
  );
}
