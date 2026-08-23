/**
 * Toast Notification System for KrishiOS.
 *
 * Provides accessible, auto-dismissing notifications stacked in a fixed container.
 */

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
  type ReactNode,
} from 'react';
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from 'lucide-react';

export type ToastVariant = 'success' | 'error' | 'info' | 'warning';

export interface ToastOptions {
  title: string;
  message?: string;
  variant?: ToastVariant;
  duration?: number;
}

export interface ToastItem extends ToastOptions {
  id: string;
}

export interface ToastContextType {
  showToast: (options: ToastOptions) => string;
  dismissToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

const variantStyles: Record<
  ToastVariant,
  {
    container: string;
    icon: string;
    IconComponent: React.ComponentType<{ className?: string; 'aria-hidden'?: boolean | 'true' | 'false' }>;
  }
> = {
  success: {
    container: 'bg-surface border-success-500 text-text',
    icon: 'text-success-600',
    IconComponent: CheckCircle2,
  },
  error: {
    container: 'bg-surface border-danger-500 text-text',
    icon: 'text-danger-600',
    IconComponent: AlertCircle,
  },
  warning: {
    container: 'bg-surface border-warning-500 text-text',
    icon: 'text-warning-600',
    IconComponent: AlertTriangle,
  },
  info: {
    container: 'bg-surface border-info-500 text-text',
    icon: 'text-info-600',
    IconComponent: Info,
  },
};

interface ToastMessageProps {
  toast: ToastItem;
  onDismiss: (id: string) => void;
}

const ToastMessage: React.FC<ToastMessageProps> = ({ toast, onDismiss }) => {
  const variant = toast.variant || 'info';
  const { container, icon, IconComponent } = variantStyles[variant];

  return (
    <div
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
      className={`pointer-events-auto flex items-start gap-3 w-full max-w-sm rounded-lg border-l-4 p-4 shadow-overlay bg-surface border-border animate-fade-in transition-all duration-200 ${container}`}
    >
      <div className={`shrink-0 mt-0.5 ${icon}`}>
        <IconComponent className="w-5 h-5" aria-hidden="true" />
      </div>

      <div className="flex-1 min-w-0">
        <h4 className="text-small font-semibold text-text">{toast.title}</h4>
        {toast.message && (
          <p className="mt-0.5 text-caption text-text-secondary leading-relaxed">
            {toast.message}
          </p>
        )}
      </div>

      <button
        type="button"
        onClick={() => onDismiss(toast.id)}
        className="shrink-0 text-text-muted hover:text-text p-1 rounded transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-primary-500"
        aria-label="Dismiss notification"
      >
        <X className="w-4 h-4" aria-hidden="true" />
      </button>
    </div>
  );
};

export interface ToastProviderProps {
  children: ReactNode;
}

export const ToastProvider: React.FC<ToastProviderProps> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(
    (options: ToastOptions): string => {
      const id = `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
      const duration = options.duration ?? 5000;

      const newToast: ToastItem = {
        ...options,
        id,
      };

      setToasts((prev) => [...prev, newToast]);

      if (duration > 0) {
        setTimeout(() => {
          dismissToast(id);
        }, duration);
      }

      return id;
    },
    [dismissToast],
  );

  const contextValue = useMemo(
    () => ({
      showToast,
      dismissToast,
    }),
    [showToast, dismissToast],
  );

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      {/* Toast container: bottom-right on sm+, bottom-center on mobile */}
      <div
        className="fixed z-50 pointer-events-none bottom-4 left-4 right-4 sm:left-auto sm:right-4 flex flex-col gap-2.5 max-w-sm w-full"
        aria-live="polite"
        aria-label="Notifications"
      >
        {toasts.map((toast) => (
          <ToastMessage key={toast.id} toast={toast} onDismiss={dismissToast} />
        ))}
      </div>
    </ToastContext.Provider>
  );
};

export function useToast(): ToastContextType {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

export default ToastProvider;
