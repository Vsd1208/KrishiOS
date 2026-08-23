/**
 * OfficerShell Component.
 *
 * Desktop-first layout for agricultural officers, agronomists, and administrators.
 * Includes a collapsible sidebar with navigation, top header, and fluid content area.
 */

import React, { useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { Header } from '@/components/layout/Header';
import {
  LayoutDashboard,
  Users,
  ClipboardCheck,
  BookOpen,
  BarChart3,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
} from 'lucide-react';

interface OfficerNavItem {
  id: string;
  label: string;
  path: string;
  icon: React.ComponentType<{ className?: string; 'aria-hidden'?: boolean | 'true' | 'false' }>;
  isActive: (pathname: string) => boolean;
}

const officerNavItems: OfficerNavItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    path: '/officer',
    icon: LayoutDashboard,
    isActive: (pathname) => pathname === '/officer' || pathname === '/officer/',
  },
  {
    id: 'farmers',
    label: 'Farmers',
    path: '/officer/farmers',
    icon: Users,
    isActive: (pathname) => pathname.startsWith('/officer/farmers'),
  },
  {
    id: 'reviews',
    label: 'Reviews',
    path: '/officer/reviews',
    icon: ClipboardCheck,
    isActive: (pathname) => pathname.startsWith('/officer/reviews'),
  },
  {
    id: 'knowledge',
    label: 'Knowledge Base',
    path: '/officer/knowledge',
    icon: BookOpen,
    isActive: (pathname) => pathname.startsWith('/officer/knowledge'),
  },
  {
    id: 'analytics',
    label: 'Analytics',
    path: '/officer/analytics',
    icon: BarChart3,
    isActive: (pathname) => pathname.startsWith('/officer/analytics'),
  },
];

export const OfficerShell: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [isCollapsed, setIsCollapsed] = useState<boolean>(false);

  return (
    <div className="min-h-screen bg-surface-raised flex flex-col">
      {/* Top Header */}
      <Header user={user} onLogout={logout} />

      <div className="flex-1 flex flex-row">
        {/* Collapsible Sidebar */}
        <aside
          aria-label="Officer Navigation"
          className={`bg-surface border-r border-border flex flex-col transition-all duration-200 shrink-0 ${
            isCollapsed ? 'w-16' : 'w-60'
          }`}
        >
          {/* Sidebar Header / Section Badge */}
          <div className="p-3 border-b border-border flex items-center justify-between">
            {!isCollapsed && (
              <div className="flex items-center gap-2 px-1">
                <ShieldCheck className="w-4 h-4 text-primary-600" aria-hidden="true" />
                <span className="text-caption font-semibold text-text-secondary uppercase tracking-wider">
                  Officer Console
                </span>
              </div>
            )}
            <button
              type="button"
              onClick={() => setIsCollapsed(!isCollapsed)}
              className={`p-1.5 rounded-md text-text-muted hover:text-text hover:bg-surface-raised transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-primary-500 ${
                isCollapsed ? 'mx-auto' : ''
              }`}
              aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {isCollapsed ? (
                <ChevronRight className="w-4 h-4" aria-hidden="true" />
              ) : (
                <ChevronLeft className="w-4 h-4" aria-hidden="true" />
              )}
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="flex-1 py-3 px-2 space-y-1">
            {officerNavItems.map((item) => {
              const active = item.isActive(location.pathname);
              const Icon = item.icon;

              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => navigate(item.path)}
                  title={isCollapsed ? item.label : undefined}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-small transition-colors select-none text-left cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 ${
                    active
                      ? 'bg-primary-50 text-primary-800 font-semibold border-l-2 border-primary-600'
                      : 'text-text-secondary hover:text-text hover:bg-surface-raised font-normal'
                  } ${isCollapsed ? 'justify-center px-2' : ''}`}
                  aria-current={active ? 'page' : undefined}
                >
                  <Icon
                    className={`w-5 h-5 shrink-0 ${active ? 'text-primary-600' : 'text-text-muted'}`}
                    aria-hidden="true"
                  />
                  {!isCollapsed && <span className="truncate">{item.label}</span>}
                </button>
              );
            })}
          </nav>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 w-full max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default OfficerShell;
