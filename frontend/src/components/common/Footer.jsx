import React from 'react';
import { Link } from 'react-router-dom';
import { Home } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="bg-gray-900 text-gray-400 py-12 mt-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div>
            <div className="flex items-center gap-2 text-white font-bold text-lg mb-3">
              <Home size={20} className="text-primary-500" />
              SmartRentAI
            </div>
            <p className="text-sm">AI-powered house rental platform for Sri Lanka.</p>
          </div>
          <div>
            <h4 className="text-white font-semibold mb-3">Search</h4>
            <ul className="space-y-2 text-sm">
              <li><Link to="/search" className="hover:text-white transition-colors">Browse Properties</Link></li>
              <li><Link to="/predict-price" className="hover:text-white transition-colors">Price Prediction</Link></li>
              <li><Link to="/recommendations" className="hover:text-white transition-colors">AI Recommendations</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="text-white font-semibold mb-3">Platform</h4>
            <ul className="space-y-2 text-sm">
              <li><Link to="/chatbot" className="hover:text-white transition-colors">AI Assistant</Link></li>
              <li><Link to="/register" className="hover:text-white transition-colors">Create Account</Link></li>
              <li><Link to="/add-property" className="hover:text-white transition-colors">List Property</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="text-white font-semibold mb-3">Districts</h4>
            <ul className="space-y-2 text-sm">
              {['Colombo','Kandy','Galle','Negombo','Kurunegala'].map(d => (
                <li key={d}><Link to={`/search?district=${d}`} className="hover:text-white transition-colors">{d}</Link></li>
              ))}
            </ul>
          </div>
        </div>
        <div className="border-t border-gray-800 mt-8 pt-6 text-center text-sm">
          © {new Date().getFullYear()} SmartRentAI — Final Year Project by A.G. Menuja Dulnidu Bandara
        </div>
      </div>
    </footer>
  );
}
