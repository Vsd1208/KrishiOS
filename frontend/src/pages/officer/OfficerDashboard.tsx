/**
 * OfficerDashboard Page.
 *
 * Console for agricultural officers, agronomists, and system reviewers.
 * Displays advisory review queues, active district alerts, and farmer metrics.
 */

import React from 'react';
import { useAuth } from '@/hooks/useAuth';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import {
  ClipboardCheck,
  AlertTriangle,
  Users,
  BookOpen,
  CheckCircle,
  Clock,
  ArrowUpRight,
} from 'lucide-react';

export const OfficerDashboard: React.FC = () => {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <section className="bg-surface border border-border rounded-xl p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-display font-bold text-text tracking-tight">
              Officer Console
            </h1>
            <p className="text-body text-text-secondary">
              Agricultural intelligence &amp; review dashboard
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-small text-text-secondary">Logged in as:</span>
            <span className="px-3 py-1 rounded-full text-small font-semibold bg-info-50 text-info-700 border border-info-200 capitalize">
              {user?.role || 'Officer'}
            </span>
          </div>
        </div>
      </section>

      {/* Key Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Pending Reviews Card */}
        <Card variant="raised" padding="md">
          <CardHeader className="mb-2">
            <div className="flex items-center justify-between">
              <span className="text-small font-medium text-text-secondary">Pending Reviews</span>
              <div className="w-8 h-8 rounded-lg bg-warning-50 text-warning-600 flex items-center justify-center">
                <ClipboardCheck className="w-5 h-5" aria-hidden="true" />
              </div>
            </div>
            <CardTitle as="h3" className="text-heading font-bold text-text">
              14
            </CardTitle>
            <CardDescription>Advisories awaiting expert verification</CardDescription>
          </CardHeader>
          <CardContent className="space-y-0 text-caption text-text-secondary pt-2 border-t border-border flex items-center justify-between">
            <span className="text-warning-600 font-medium flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" aria-hidden="true" /> 4 urgent
            </span>
            <span className="text-text-muted">Avg response: 18m</span>
          </CardContent>
        </Card>

        {/* Active Alerts Card */}
        <Card variant="raised" padding="md">
          <CardHeader className="mb-2">
            <div className="flex items-center justify-between">
              <span className="text-small font-medium text-text-secondary">Active Alerts</span>
              <div className="w-8 h-8 rounded-lg bg-danger-50 text-danger-600 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5" aria-hidden="true" />
              </div>
            </div>
            <CardTitle as="h3" className="text-heading font-bold text-text">
              6
            </CardTitle>
            <CardDescription>Disease &amp; weather advisories live</CardDescription>
          </CardHeader>
          <CardContent className="space-y-0 text-caption text-text-secondary pt-2 border-t border-border flex items-center justify-between">
            <span className="text-danger-600 font-medium">3 Pest • 3 Weather</span>
            <span className="text-text-muted">Regional broadcast</span>
          </CardContent>
        </Card>

        {/* Farmers Managed Card */}
        <Card variant="raised" padding="md">
          <CardHeader className="mb-2">
            <div className="flex items-center justify-between">
              <span className="text-small font-medium text-text-secondary">Farmers Assigned</span>
              <div className="w-8 h-8 rounded-lg bg-primary-50 text-primary-600 flex items-center justify-center">
                <Users className="w-5 h-5" aria-hidden="true" />
              </div>
            </div>
            <CardTitle as="h3" className="text-heading font-bold text-text">
              248
            </CardTitle>
            <CardDescription>Across 12 mandals in jurisdiction</CardDescription>
          </CardHeader>
          <CardContent className="space-y-0 text-caption text-text-secondary pt-2 border-t border-border flex items-center justify-between">
            <span className="text-success-600 font-medium flex items-center gap-0.5">
              <ArrowUpRight className="w-3.5 h-3.5" aria-hidden="true" /> +12 this month
            </span>
            <span className="text-text-muted">94% active</span>
          </CardContent>
        </Card>

        {/* Knowledge Base Status Card */}
        <Card variant="raised" padding="md">
          <CardHeader className="mb-2">
            <div className="flex items-center justify-between">
              <span className="text-small font-medium text-text-secondary">Knowledge Graph</span>
              <div className="w-8 h-8 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center">
                <BookOpen className="w-5 h-5" aria-hidden="true" />
              </div>
            </div>
            <CardTitle as="h3" className="text-heading font-bold text-text">
              1,840
            </CardTitle>
            <CardDescription>Validated agronomic entities</CardDescription>
          </CardHeader>
          <CardContent className="space-y-0 text-caption text-text-secondary pt-2 border-t border-border flex items-center justify-between">
            <span className="text-success-600 font-medium flex items-center gap-1">
              <CheckCircle className="w-3.5 h-3.5" aria-hidden="true" /> Synced
            </span>
            <span className="text-text-muted">Sprint 10 Graph</span>
          </CardContent>
        </Card>
      </div>

      {/* Review Queue Summary Section */}
      <section className="space-y-4">
        <h2 className="text-subheading font-semibold text-text">Pending Advisory Review Queue</h2>
        <Card variant="default" padding="none" className="overflow-hidden">
          <div className="p-4 sm:p-6 border-b border-border bg-surface-raised/40">
            <p className="text-small text-text-secondary">
              Review agent recommendations requiring agronomist verification before sending to farmers.
            </p>
          </div>
          <div className="divide-y divide-border">
            <div className="p-4 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-surface-raised transition-colors">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-caption font-semibold bg-danger-50 text-danger-700">
                    High Priority
                  </span>
                  <span className="text-small font-semibold text-text">
                    Stem Borer Chemical Treatment Advisory
                  </span>
                </div>
                <p className="text-small text-text-secondary">
                  Farmer: Ramesh Rao (Warangal) • Crop: Paddy (BPT 5204)
                </p>
              </div>
              <span className="text-caption text-text-muted">Submitted 25m ago</span>
            </div>

            <div className="p-4 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-surface-raised transition-colors">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-caption font-semibold bg-warning-50 text-warning-700">
                    Medium Priority
                  </span>
                  <span className="text-small font-semibold text-text">
                    Pre-monsoon Fertilizer Schedule Revision
                  </span>
                </div>
                <p className="text-small text-text-secondary">
                  Farmer: Venkat Reddy (Karimnagar) • Crop: Cotton
                </p>
              </div>
              <span className="text-caption text-text-muted">Submitted 1h ago</span>
            </div>
          </div>
        </Card>
      </section>
    </div>
  );
};

export default OfficerDashboard;
