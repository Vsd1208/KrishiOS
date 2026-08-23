/**
 * Header Component for KrishiOS.
 *
 * Universal app header with KrishiOS branding, multilingual language selector,
 * user role badge, and sign-out controls.
 */

import React from 'react';
import type { AuthUser, UserRole } from '@/types/auth';
import { Sprout, LogOut, Globe, User as UserIcon } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export interface HeaderProps {
  user: AuthUser | null;
  onLogout: () => void;
  onToggleSidebar?: () => void;
  className?: string;
}

const roleBadgeColors: Record<UserRole, { bg: string; text: string; border: string }> = {
  farmer: {
    bg: 'bg-primary-50',
    text: 'text-primary-700',
    border: 'border-primary-200',
  },
  officer: {
    bg: 'bg-info-50',
    text: 'text-info-700',
    border: 'border-info-100',
  },
  agronomist: {
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    border: 'border-emerald-200',
  },
  admin: {
    bg: 'bg-purple-50',
    text: 'text-purple-700',
    border: 'border-purple-200',
  },
  system: {
    bg: 'bg-gray-100',
    text: 'text-gray-700',
    border: 'border-gray-300',
  },
};

export const Header: React.FC<HeaderProps> = ({
  user,
  onLogout,
  className = '',
}) => {
  const [currentLang, setCurrentLang] = React.useState<string>('en');

  const roleStyle = user?.role
    ? roleBadgeColors[user.role] || roleBadgeColors.farmer
    : roleBadgeColors.farmer;

  return (
    <header
      className={`bg-surface border-b border-border sticky top-0 z-30 px-4 py-2.5 sm:px-6 transition-colors shadow-sm ${className}`}
    >
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-3">
        {/* Left: Branding */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 select-none">
            <div className="w-8 h-8 rounded-lg bg-primary-600 text-white flex items-center justify-center shadow-sm">
              <Sprout className="w-5 h-5" aria-hidden="true" />
            </div>
            <div className="flex flex-col">
              <span className="text-subheading font-bold text-text tracking-tight leading-none">
                KrishiOS
              </span>
              <span className="text-[10px] text-text-muted font-medium uppercase tracking-wider leading-tight hidden sm:block">
                AI Agricultural Intelligence
              </span>
            </div>
          </div>
        </div>

        {/* Right: Controls, Language, Profile, Logout */}
        <div className="flex items-center gap-2 sm:gap-4">
          {/* Language Selector */}
          <div className="relative flex items-center">
            <label htmlFor="language-selector" className="sr-only">
              Select Language
            </label>
            <Globe className="w-4 h-4 text-text-muted absolute left-2.5 pointer-events-none" aria-hidden="true" />
            <select
              id="language-selector"
              value={currentLang}
              onChange={(e) => setCurrentLang(e.target.value)}
              className="appearance-none pl-8 pr-7 py-1.5 text-small bg-surface-raised border border-border rounded-md text-text font-medium hover:border-border-strong focus:outline-none focus-visible:ring-1 focus-visible:ring-primary-500 cursor-pointer min-h-[36px]"
            >
              <option value="en">English</option>
              <option value="te">తెలుగు (Telugu)</option>
              <option value="hi">हिन्दी (Hindi)</option>
            </select>
            <span className="absolute right-2.5 pointer-events-none text-caption text-text-muted">
              ▼
            </span>
          </div>

          {/* User Profile Info & Role Badge */}
          {user && (
            <div className="flex items-center gap-2">
              <div
                className={`hidden md:inline-flex items-center px-2.5 py-0.5 rounded-full text-caption font-medium border capitalize ${roleStyle.bg} ${roleStyle.text} ${roleStyle.border}`}
              >
                {user.role}
              </div>

              <div
                className="hidden lg:flex items-center gap-1.5 text-small text-text-secondary"
                title={`User ID: ${user.uuid}`}
              >
                <div className="w-7 h-7 rounded-full bg-surface-raised border border-border flex items-center justify-center text-text-secondary">
                  <UserIcon className="w-4 h-4" aria-hidden="true" />
                </div>
                <span className="font-mono text-caption text-text-muted max-w-[80px] truncate">
                  {user.uuid.slice(0, 8)}
                </span>
              </div>
            </div>
          )}

          {/* Logout Button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={onLogout}
            className="text-text-secondary hover:text-danger-600 hover:bg-danger-50 min-h-[36px]"
            aria-label="Sign out of KrishiOS"
            leftIcon={<LogOut className="w-4 h-4" aria-hidden="true" />}
          >
            <span className="hidden sm:inline">Sign Out</span>
          </Button>
        </div>
      </div>
    </header>
  );
};

export default Header;
