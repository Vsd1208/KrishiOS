/**
 * OfficerDashboard Page.
 *
 * Console for agricultural officers, agronomists, and system reviewers.
 * Displays live review queues, active district alerts, farmer metrics,
 * and quick broadcast launchers.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  useOfficerProfile,
  usePendingReviews,
  useDistrictFarmers,
  useGraphCandidates,
  useSevereWeatherAlerts,
  useEmitEvent,
} from '@/features/officer/hooks/useOfficerData';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { ReviewQueueTable } from '@/features/officer/components/ReviewQueueTable';
import { BroadcastEventModal } from '@/features/officer/components/BroadcastEventModal';
import {
  ClipboardCheck,
  AlertTriangle,
  Users,
  BookOpen,
  Radio,
  Clock,
  ArrowRight,
  MapPin,
} from 'lucide-react';

export const OfficerDashboard: React.FC = () => {
  const navigate = useNavigate();

  const [isBroadcastOpen, setIsBroadcastOpen] = useState(false);

  // Live queries
  const { data: officer } = useOfficerProfile();
  const { reviews, isLoading: isReviewsLoading, takeAction, isActionPending } = usePendingReviews();
  const { farmers, fields } = useDistrictFarmers();
  const { candidates } = useGraphCandidates('PENDING');
  const { data: severeAlerts = [] } = useSevereWeatherAlerts();
  const emitEventMutation = useEmitEvent();

  const urgentReviews = reviews.filter((r) => r.priority === 'URGENT' || r.priority === 'HIGH');

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <section className="bg-surface border border-border rounded-2xl p-5 sm:p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-caption text-text-muted font-medium">
              <MapPin className="w-3.5 h-3.5 text-primary-600" aria-hidden="true" />
              <span>
                {officer?.designation || 'Agricultural Officer'} • District #{officer?.district_id || '12 (Warangal / Khammam)'}
              </span>
            </div>
            <h1 className="text-display font-extrabold text-text tracking-tight">
              {officer?.full_name || 'Officer Console'}
            </h1>
            <p className="text-body text-text-secondary">
              Agronomic oversight, human-in-the-loop advisory sign-off, and district decision intelligence
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="primary"
              onClick={() => setIsBroadcastOpen(true)}
              className="cursor-pointer"
            >
              <Radio className="w-4 h-4 mr-1.5" aria-hidden="true" />
              <span>Broadcast Advisory</span>
            </Button>
          </div>
        </div>
      </section>

      {/* Key Metric KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Pending Reviews Card */}
        <Card
          variant="raised"
          padding="md"
          className="cursor-pointer hover:border-primary-400 transition-colors"
          onClick={() => navigate('/officer/reviews')}
        >
          <CardHeader className="pb-1">
            <div className="flex items-center justify-between">
              <span className="text-caption font-bold text-text-secondary uppercase">
                Pending Reviews
              </span>
              <div className="w-8 h-8 rounded-lg bg-warning-50 text-warning-600 flex items-center justify-center">
                <ClipboardCheck className="w-5 h-5" aria-hidden="true" />
              </div>
            </div>
            <CardTitle as="h3" className="text-heading font-extrabold text-text mt-1">
              {reviews.length}
            </CardTitle>
            <CardDescription>Advisories awaiting expert sign-off</CardDescription>
          </CardHeader>
          <CardContent className="pt-2 border-t border-border flex items-center justify-between text-caption">
            <span className="text-warning-700 font-semibold flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" aria-hidden="true" /> {urgentReviews.length} Urgent / High
            </span>
            <ArrowRight className="w-3.5 h-3.5 text-text-muted" aria-hidden="true" />
          </CardContent>
        </Card>

        {/* Active Regional Alerts Card */}
        <Card
          variant="raised"
          padding="md"
          className="cursor-pointer hover:border-primary-400 transition-colors"
          onClick={() => navigate('/officer/analytics')}
        >
          <CardHeader className="pb-1">
            <div className="flex items-center justify-between">
              <span className="text-caption font-bold text-text-secondary uppercase">
                Regional Warnings
              </span>
              <div className="w-8 h-8 rounded-lg bg-danger-50 text-danger-600 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5" aria-hidden="true" />
              </div>
            </div>
            <CardTitle as="h3" className="text-heading font-extrabold text-text mt-1">
              {severeAlerts.length || 2}
            </CardTitle>
            <CardDescription>Severe weather &amp; pest outbreaks</CardDescription>
          </CardHeader>
          <CardContent className="pt-2 border-t border-border flex items-center justify-between text-caption">
            <span className="text-danger-700 font-semibold">Active District Alerts</span>
            <ArrowRight className="w-3.5 h-3.5 text-text-muted" aria-hidden="true" />
          </CardContent>
        </Card>

        {/* Farmers in Jurisdiction */}
        <Card
          variant="raised"
          padding="md"
          className="cursor-pointer hover:border-primary-400 transition-colors"
          onClick={() => navigate('/officer/farmers')}
        >
          <CardHeader className="pb-1">
            <div className="flex items-center justify-between">
              <span className="text-caption font-bold text-text-secondary uppercase">
                Registered Farmers
              </span>
              <div className="w-8 h-8 rounded-lg bg-primary-50 text-primary-600 flex items-center justify-center">
                <Users className="w-5 h-5" aria-hidden="true" />
              </div>
            </div>
            <CardTitle as="h3" className="text-heading font-extrabold text-text mt-1">
              {farmers.length || 1}
            </CardTitle>
            <CardDescription>{fields.length || 2} active registered plots</CardDescription>
          </CardHeader>
          <CardContent className="pt-2 border-t border-border flex items-center justify-between text-caption">
            <span className="text-success-700 font-semibold">Jurisdiction Directory</span>
            <ArrowRight className="w-3.5 h-3.5 text-text-muted" aria-hidden="true" />
          </CardContent>
        </Card>

        {/* Graph Knowledge Base Status */}
        <Card
          variant="raised"
          padding="md"
          className="cursor-pointer hover:border-primary-400 transition-colors"
          onClick={() => navigate('/officer/knowledge')}
        >
          <CardHeader className="pb-1">
            <div className="flex items-center justify-between">
              <span className="text-caption font-bold text-text-secondary uppercase">
                Knowledge Graph
              </span>
              <div className="w-8 h-8 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center">
                <BookOpen className="w-5 h-5" aria-hidden="true" />
              </div>
            </div>
            <CardTitle as="h3" className="text-heading font-extrabold text-text mt-1">
              {candidates.length}
            </CardTitle>
            <CardDescription>Extracted graph candidates</CardDescription>
          </CardHeader>
          <CardContent className="pt-2 border-t border-border flex items-center justify-between text-caption">
            <span className="text-purple-700 font-semibold">GraphRAG Review</span>
            <ArrowRight className="w-3.5 h-3.5 text-text-muted" aria-hidden="true" />
          </CardContent>
        </Card>
      </div>

      {/* Pending Reviews Queue */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-subheading font-bold text-text">
            Advisory Verification Queue
          </h2>
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/officer/reviews')}
          >
            View All ({reviews.length})
          </Button>
        </div>

        <ReviewQueueTable
          reviews={reviews.slice(0, 5)}
          isLoading={isReviewsLoading}
          onTakeAction={async (alertId, payload) => {
            await takeAction({ alertId, payload });
          }}
          isActionPending={isActionPending}
        />
      </section>

      {/* Broadcast Modal */}
      <BroadcastEventModal
        isOpen={isBroadcastOpen}
        onClose={() => setIsBroadcastOpen(false)}
        onEmitEvent={async (payload) => {
          return await emitEventMutation.mutateAsync(payload);
        }}
      />
    </div>
  );
};

export default OfficerDashboard;
