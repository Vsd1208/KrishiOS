/**
 * ReviewQueuePage Component.
 *
 * Full Human-in-the-Loop Advisory Review Page for Agricultural Officers.
 * Allows filtering, full inspection of telemetry and ICAR citations,
 * inline message editing, and verification sign-off.
 */

import React, { useState } from 'react';
import { usePendingReviews } from '@/features/officer/hooks/useOfficerData';
import { ReviewQueueTable } from '@/features/officer/components/ReviewQueueTable';
import { RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export const ReviewQueuePage: React.FC = () => {
  const [priorityFilter, setPriorityFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const { reviews, isLoading, refetch, isFetching, takeAction, isActionPending } =
    usePendingReviews();

  const filteredReviews = reviews.filter((r) => {
    if (priorityFilter !== 'ALL' && r.priority !== priorityFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        r.title.toLowerCase().includes(q) ||
        r.message.toLowerCase().includes(q) ||
        String(r.farmer_id).includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-display font-extrabold text-text tracking-tight">
            Advisory Review Queue
          </h1>
          <p className="text-body text-text-secondary">
            Verify, customize, and sign off on high-impact AI recommendations before farmer delivery
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
            className="cursor-pointer"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 mr-1.5 ${isFetching ? 'animate-spin' : ''}`}
              aria-hidden="true"
            />
            <span>Refresh</span>
          </Button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-3 rounded-xl bg-surface border border-border flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
        {/* Priority Tabs */}
        <div className="flex gap-1 overflow-x-auto pb-1 sm:pb-0">
          {['ALL', 'URGENT', 'HIGH', 'NORMAL', 'LOW'].map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setPriorityFilter(p)}
              className={`px-3 py-1.5 rounded-lg text-caption font-bold transition-colors cursor-pointer ${
                priorityFilter === p
                  ? 'bg-primary-600 text-white shadow-sm'
                  : 'bg-surface-raised text-text-secondary hover:text-text'
              }`}
            >
              {p}
            </button>
          ))}
        </div>

        {/* Text Search */}
        <div className="w-full sm:w-72">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by farmer ID, crop, or topic..."
            className="w-full px-3 py-1.5 rounded-lg bg-surface-raised border border-border text-small text-text placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
      </div>

      {/* Review Queue Table */}
      <ReviewQueueTable
        reviews={filteredReviews}
        isLoading={isLoading}
        onTakeAction={async (alertId, payload) => {
          await takeAction({ alertId, payload });
        }}
        isActionPending={isActionPending}
      />
    </div>
  );
};

export default ReviewQueuePage;
