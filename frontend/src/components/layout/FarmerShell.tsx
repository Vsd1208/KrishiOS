/**
 * FarmerShell Component.
 *
 * Mobile-first application layout for farmers.
 * Features a top header, scrollable content viewport, and a fixed bottom tab bar
 * with intuitive navigation for touch devices.
 */

import React from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { Header } from '@/components/layout/Header';
import { Home, Sparkles, MapPin, Bell, User } from 'lucide-react';

interface FarmerNavTab {
  id: string;
  label: string;
  path: string;
  icon: React.ComponentType<{ className?: string; 'aria-hidden'?: boolean | 'true' | 'false' }>;
  isActive: (pathname: string) => boolean;
}

const farmerTabs: FarmerNavTab[] = [
  {
    id: 'home',
    label: 'Home',
    path: '/farmer',
    icon: Home,
    isActive: (pathname) => pathname === '/farmer' || pathname === '/farmer/',
  },
  {
    id: 'ask',
    label: 'Ask AI',
    path: '/farmer/ask',
    icon: Sparkles,
    isActive: (pathname) => pathname.startsWith('/farmer/ask'),
  },
  {
    id: 'fields',
    label: 'Fields',
    path: '/farmer/fields',
    icon: MapPin,
    isActive: (pathname) => pathname.startsWith('/farmer/fields'),
  },
  {
    id: 'alerts',
    label: 'Alerts',
    path: '/farmer/alerts',
    icon: Bell,
    isActive: (pathname) => pathname.startsWith('/farmer/alerts'),
  },
  {
    id: 'profile',
    label: 'Profile',
    path: '/farmer/profile',
    icon: User,
    isActive: (pathname) => pathname.startsWith('/farmer/profile'),
  },
];

export const FarmerShell: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-surface-raised flex flex-col">
      {/* Top Header */}
      <Header user={user} onLogout={logout} />

      {/* Main Content Area — bottom padded to prevent bottom nav overlay */}
      <main className="flex-1 w-full max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8 pb-24 md:pb-8">
        <Outlet />
      </main>

      {/* Mobile-first Bottom Navigation Bar */}
      <nav
        aria-label="Farmer Navigation"
        className="fixed bottom-0 left-0 right-0 z-40 bg-surface border-t border-border shadow-lg"
      >
        <div className="max-w-md mx-auto flex items-center justify-around h-16 px-1">
          {farmerTabs.map((tab) => {
            const active = tab.isActive(location.pathname);
            const Icon = tab.icon;

            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => navigate(tab.path)}
                className={`flex-1 flex flex-col items-center justify-center h-full py-1 px-1 rounded-lg transition-colors cursor-pointer select-none focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 ${
                  active
                    ? 'text-primary-600 font-semibold'
                    : 'text-text-muted hover:text-text hover:bg-surface-raised active:bg-gray-100 font-normal'
                }`}
                aria-current={active ? 'page' : undefined}
              >
                <div className="relative">
                  <Icon
                    className={`w-5 h-5 transition-transform ${active ? 'scale-110' : ''}`}
                    aria-hidden="true"
                  />
                  {active && (
                    <span
                      className="absolute -top-1 -right-1 w-1.5 h-1.5 rounded-full bg-primary-600"
                      aria-hidden="true"
                    />
                  )}
                </div>
                <span className="text-[11px] mt-1 tracking-tight leading-none">
                  {tab.label}
                </span>
              </button>
            );
          })}
        </div>
      </nav>
    </div>
  );
};

export default FarmerShell;
