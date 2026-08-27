import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import { logout } from '../../store/slices/authSlice';
import { Home, Search, Heart, Star, TrendingUp, MessageCircle, User, LogOut, Menu, X, Shield, MapPin } from 'lucide-react';

export default function Navbar() {
  const { user } = useSelector((s) => s.auth);
  const dispatch  = useDispatch();
  const navigate  = useNavigate();
  const [open, setOpen]   = useState(false);
  const [drop, setDrop]   = useState(false);

  const handleLogout = () => {
    dispatch(logout());
    navigate('/');
    setDrop(false);
  };

  const navLinks = [
    { to: '/search',          icon: <Search size={16} />,       label: 'Search' },
    { to: '/predict-price',   icon: <TrendingUp size={16} />,   label: 'Price AI' },
    { to: '/chatbot',         icon: <MessageCircle size={16} />, label: 'AI Chat' },
    { to: '/safety',          icon: <MapPin size={16} />,        label: 'SafeRent' },
    ...(user ? [
      { to: '/recommendations', icon: <Star size={16} />,    label: 'For You' },
      { to: '/wishlist',        icon: <Heart size={16} />,   label: 'Wishlist' },
    ] : []),
  ];

  return (
    <nav className="sticky top-0 z-50 bg-white dark:bg-gray-950 border-b border-gray-200 dark:border-gray-800 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 font-bold text-xl text-primary-600">
            <Home size={24} />
            Smart<span className="text-gray-900 dark:text-white">RentAI</span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-1">
            {navLinks.map((l) => (
              <Link key={l.to} to={l.to}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium text-gray-600
                           hover:text-primary-600 hover:bg-primary-50 dark:text-gray-300 dark:hover:bg-gray-800 transition-all">
                {l.icon}{l.label}
              </Link>
            ))}
          </div>

          {/* Auth */}
          <div className="hidden md:flex items-center gap-3">
            {user ? (
              <div className="relative">
                <button onClick={() => setDrop(!drop)}
                  className="flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 transition-all">
                  <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center text-white text-sm font-semibold">
                    {user.full_name?.[0]?.toUpperCase()}
                  </div>
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{user.full_name?.split(' ')[0]}</span>
                </button>
                {drop && (
                  <div className="absolute right-0 mt-2 w-52 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg py-1 z-50">
                    <Link to="/profile" onClick={() => setDrop(false)}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300">
                      <User size={16} /> Profile
                    </Link>
                    {(user.role === 'landlord' || user.role === 'admin') && (
                      <Link to="/add-property" onClick={() => setDrop(false)}
                        className="flex items-center gap-2 px-4 py-2.5 text-sm hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300">
                        <Home size={16} /> Add Property
                      </Link>
                    )}
                    {user.role === 'admin' && (
                      <Link to="/admin" onClick={() => setDrop(false)}
                        className="flex items-center gap-2 px-4 py-2.5 text-sm hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300">
                        <Shield size={16} /> Admin Panel
                      </Link>
                    )}
                    <hr className="my-1 border-gray-200 dark:border-gray-700" />
                    <button onClick={handleLogout}
                      className="flex items-center gap-2 w-full px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20">
                      <LogOut size={16} /> Logout
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <>
                <Link to="/login"    className="btn-secondary text-sm">Login</Link>
                <Link to="/register" className="btn-primary  text-sm">Get Started</Link>
              </>
            )}
          </div>

          {/* Mobile menu button */}
          <button className="md:hidden p-2" onClick={() => setOpen(!open)}>
            {open ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden bg-white dark:bg-gray-950 border-t border-gray-200 dark:border-gray-800 px-4 py-3 space-y-1">
          {navLinks.map((l) => (
            <Link key={l.to} to={l.to} onClick={() => setOpen(false)}
              className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-50 dark:text-gray-300">
              {l.icon}{l.label}
            </Link>
          ))}
          {user ? (
            <button onClick={handleLogout} className="flex items-center gap-2 w-full px-3 py-2.5 text-sm text-red-600">
              <LogOut size={16} /> Logout
            </button>
          ) : (
            <div className="flex gap-2 pt-2">
              <Link to="/login"    className="btn-secondary flex-1 text-center text-sm" onClick={() => setOpen(false)}>Login</Link>
              <Link to="/register" className="btn-primary  flex-1 text-center text-sm" onClick={() => setOpen(false)}>Register</Link>
            </div>
          )}
        </div>
      )}
    </nav>
  );
}
