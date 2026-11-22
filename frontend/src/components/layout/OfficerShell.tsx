/**
 * OfficerShell Component.
 *
 * Desktop-first layout for agricultural officers, agronomists, and administrators.
 * Includes a collapsible sidebar with navigation, top header, and fluid content area.
 */

import React, { useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/hooks/useAuth';
import { Header } from '@/components/layout/Header';
import {
  FileText,
  LayoutDashboard,
  Users,
  ClipboardCheck,
  BookOpen,
  BarChart3,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  MessageSquareWarning,
  HandHelping,
  Landmark,
  Megaphone,
  Activity,
  LifeBuoy,
  Sprout,
  Bug,
} from 'lucide-react';
import type { UserRole } from '@/types/auth';

interface OfficerNavItem {
  id: string;
  label: string;
  path: string;
  icon: React.ComponentType<{ className?: string; 'aria-hidden'?: boolean | 'true' | 'false' }>;
  isActive: (pathname: string) => boolean;
  /** Roles that see this item; defaults to officer roles. */
  roles?: UserRole[];
}

const OFFICER_ROLES: UserRole[] = ['officer', 'agronomist', 'admin'];

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
  {
    id: 'evaluation',
    label: 'Trust & Evaluation',
    path: '/officer/evaluation',
    icon: ShieldCheck,
    isActive: (pathname) => pathname.startsWith('/officer/evaluation'),
  },
  {
    id: 'bulletins',
    label: 'Bulletins',
    path: '/officer/bulletins',
    icon: Landmark,
    isActive: (pathname) => pathname.startsWith('/officer/bulletins'),
  },
  {
    id: 'publish',
    label: 'Publish Advisory',
    path: '/officer/publish',
    icon: Megaphone,
    isActive: (pathname) => pathname.startsWith('/officer/publish'),
  },
  {
    id: 'connect',
    label: 'Connect Analytics',
    path: '/officer/connect',
    icon: Activity,
    isActive: (pathname) => pathname.startsWith('/officer/connect'),
  },
  {
    id: 'grievances',
    label: 'Grievances & Schemes',
    path: '/officer/grievances',
    icon: LifeBuoy,
    isActive: (pathname) => pathname.startsWith('/officer/grievances'),
  },
  {
    id: 'yield',
    label: 'Yield Outlook',
    path: '/officer/yield',
    icon: Sprout,
    isActive: (pathname) => pathname.startsWith('/officer/yield'),
  },
  {
    id: 'outbreaks',
    label: 'Outbreaks',
    path: '/officer/outbreaks',
    icon: Bug,
    isActive: (pathname) => pathname.startsWith('/officer/outbreaks'),
  },
  {
    id: 'documents',
    label: 'Document Briefs',
    path: '/officer/documents',
    icon: FileText,
    isActive: (pathname) => pathname.startsWith('/officer/documents'),
    roles: ['officer', 'agronomist', 'admin'],
  },
  {
    id: 'feedback',
    label: 'Farmer Feedback',
    path: '/officer/feedback',
    icon: MessageSquareWarning,
    isActive: (pathname) => pathname.startsWith('/officer/feedback'),
  },
  {
    id: 'extension',
    label: 'Assisted Mode',
    path: '/officer/extension',
    icon: HandHelping,
    isActive: (pathname) => pathname.startsWith('/officer/extension'),
    roles: ['extension_worker', 'officer', 'admin'],
  },
];

export const OfficerShell: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useTranslation();
  // Start collapsed on phones so the menu does not take most of the screen width.
  const [isCollapsed, setIsCollapsed] = useState<boolean>(
    () => typeof window !== 'undefined' && window.innerWidth < 768,
  );

  return (
    <div className="min-h-screen bg-surface-raised flex flex-col">
      {/* Top Header */}
      <Header user={user} onLogout={logout} />

      <div className="flex-1 flex flex-row">
        {/* Collapsible Sidebar */}
        <aside
          aria-label={t('shell.officerNav')}
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
                  {t('shell.officerConsole')}
                </span>
              </div>
            )}
            <button
              type="button"
              onClick={() => setIsCollapsed(!isCollapsed)}
              className={`p-1.5 rounded-md text-text-muted hover:text-text hover:bg-surface-raised transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-primary-500 ${
                isCollapsed ? 'mx-auto' : ''
              }`}
              aria-label={isCollapsed ? t('shell.expandMenu') : t('shell.collapseMenu')}
              aria-expanded={!isCollapsed}
              title={isCollapsed ? t('shell.expandMenu') : t('shell.collapseMenu')}
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
            {officerNavItems
              .filter((item) => user?.role && (item.roles ?? OFFICER_ROLES).includes(user.role))
              .map((item) => {
              const active = item.isActive(location.pathname);
              const Icon = item.icon;
              const label = t(`nav.officer.${item.id}`, { defaultValue: item.label });

              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => navigate(item.path)}
                  title={isCollapsed ? label : undefined}
                  aria-label={isCollapsed ? label : undefined}
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
                  {!isCollapsed && <span className="truncate">{label}</span>}
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
