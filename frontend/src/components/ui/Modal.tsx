/**
 * @file Modal.tsx
 * @description Accessible dialog modal component for KrishiOS.
 *
 * Implements WAI-ARIA dialog specifications:
 * - Rendered into document.body using React portals.
 * - Backdrop overlay with backdrop blur.
 * - Focus trapping (Tab / Shift+Tab cycle within the dialog).
 * - Focus restoration to previously active element on close.
 * - Escape key dismissal and outside backdrop click dismissal.
 * - Body scroll locking while open.
 */

import React, { useEffect, useId, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';

export type ModalSize = 'sm' | 'md' | 'lg' | 'xl';

export interface ModalProps {
  /** Whether the modal dialog is currently visible */
  isOpen: boolean;
  /** Callback fired when the modal requests closure */
  onClose: () => void;
  /** Modal header title */
  title?: React.ReactNode;
  /** Optional subtitle or description */
  description?: React.ReactNode;
  /** Modal body content */
  children: React.ReactNode;
  /** Optional modal footer actions */
  footer?: React.ReactNode;
  /** Maximum width size variant */
  size?: ModalSize;
  /** Whether clicking the backdrop closes the modal (default: true) */
  closeOnBackdropClick?: boolean;
  /** Whether pressing Escape closes the modal (default: true) */
  closeOnEscape?: boolean;
  /** Whether to show the top-right close 'X' button (default: true) */
  showCloseButton?: boolean;
  /** Additional class names for the modal panel container */
  className?: string;
}

const sizeStyles: Record<ModalSize, string> = {
  sm: 'max-w-sm',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
};

const FOCUSABLE_SELECTOR =
  'a[href], area[href], input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), iframe, [tabindex]:not([tabindex="-1"])';

/**
 * Modal dialog component with focus trapping, portal rendering, and ARIA support.
 */
export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  footer,
  size = 'md',
  closeOnBackdropClick = true,
  closeOnEscape = true,
  showCloseButton = true,
  className = '',
}) => {
  const titleId = useId();
  const descriptionId = useId();
  const modalRef = useRef<HTMLDivElement>(null);
  const previousActiveElementRef = useRef<HTMLElement | null>(null);

  // Handle focus management and body scroll locking
  useEffect(() => {
    if (!isOpen) return;

    // Save previous active element to restore later
    if (typeof document !== 'undefined') {
      previousActiveElementRef.current = document.activeElement as HTMLElement | null;

      // Lock body scroll
      const originalOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';

      // Focus the modal or first focusable element
      const timer = setTimeout(() => {
        if (modalRef.current) {
          const focusableElements = modalRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
          if (focusableElements.length > 0 && focusableElements[0]) {
            focusableElements[0].focus();
          } else {
            modalRef.current.focus();
          }
        }
      }, 50);

      return () => {
        clearTimeout(timer);
        document.body.style.overflow = originalOverflow;
        if (previousActiveElementRef.current && typeof previousActiveElementRef.current.focus === 'function') {
          previousActiveElementRef.current.focus();
        }
      };
    }
  }, [isOpen]);

  // Handle Escape key and Tab focus trap
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (closeOnEscape && event.key === 'Escape') {
        event.stopPropagation();
        onClose();
        return;
      }

      if (event.key === 'Tab' && modalRef.current) {
        const focusableElements = Array.from(
          modalRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
        ).filter((el) => el.offsetParent !== null); // only visible elements

        if (focusableElements.length === 0) {
          event.preventDefault();
          return;
        }

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (event.shiftKey) {
          if (document.activeElement === firstElement && lastElement) {
            event.preventDefault();
            lastElement.focus();
          }
        } else {
          if (document.activeElement === lastElement && firstElement) {
            event.preventDefault();
            firstElement.focus();
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, closeOnEscape, onClose]);

  if (!isOpen || typeof document === 'undefined') {
    return null;
  }

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (closeOnBackdropClick && e.target === e.currentTarget) {
      onClose();
    }
  };

  const modalContent = (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto animate-fade-in"
      role="presentation"
    >
      {/* Backdrop overlay */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
        aria-hidden="true"
        onClick={handleBackdropClick}
      />

      {/* Modal Dialog Panel */}
      <div
        ref={modalRef}
        role="dialog"
        tabIndex={-1}
        aria-modal="true"
        aria-labelledby={title ? titleId : undefined}
        aria-describedby={description ? descriptionId : undefined}
        className={`relative z-10 w-full ${sizeStyles[size]} bg-surface rounded-xl border border-border shadow-overlay flex flex-col max-h-[90vh] overflow-hidden focus:outline-none ${className}`.trim()}
      >
        {/* Header */}
        {(title || showCloseButton) && (
          <div className="flex items-start justify-between p-5 sm:p-6 border-b border-border gap-4">
            <div className="flex flex-col gap-1">
              {title && (
                <h3 id={titleId} className="text-heading font-semibold text-text">
                  {title}
                </h3>
              )}
              {description && (
                <p id={descriptionId} className="text-small text-text-secondary">
                  {description}
                </p>
              )}
            </div>

            {showCloseButton && (
              <button
                type="button"
                onClick={onClose}
                aria-label="Close dialog"
                className="p-1.5 -mr-1.5 -mt-1.5 rounded-lg text-text-secondary hover:text-text hover:bg-surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 transition-colors"
              >
                <X className="w-5 h-5" aria-hidden="true" />
              </button>
            )}
          </div>
        )}

        {/* Body Content */}
        <div className="p-5 sm:p-6 overflow-y-auto flex-1 text-body text-text">
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div className="flex items-center justify-end gap-3 p-4 sm:p-6 border-t border-border bg-surface-raised/50">
            {footer}
          </div>
        )}
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
};

Modal.displayName = 'Modal';
