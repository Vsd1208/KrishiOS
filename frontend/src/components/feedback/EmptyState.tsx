/**
 * EmptyState Component.
 *
 * Displays placeholder messaging and an optional call-to-action when lists or resources are empty.
 */

import React from 'react';
import { Inbox } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export interface EmptyStateProps {
  title: string;
  message?: string;
  icon?: React.ReactNode;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  message,
  icon,
  action,
  className = '',
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center p-8 text-center rounded-xl border border-dashed border-border bg-surface-raised/50 ${className}`}
    >
      <div className="w-12 h-12 rounded-full bg-surface border border-border flex items-center justify-center text-text-muted mb-4 shadow-sm">
        {icon || <Inbox className="w-6 h-6" aria-hidden="true" />}
      </div>

      <h3 className="text-subheading font-semibold text-text mb-1.5">{title}</h3>

      {message && (
        <p className="text-small text-text-secondary max-w-sm mb-5 leading-relaxed">
          {message}
        </p>
      )}

      {action && (
        <Button variant="outline" size="sm" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  );
};

export default EmptyState;
