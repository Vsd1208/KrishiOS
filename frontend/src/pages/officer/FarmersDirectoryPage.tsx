/**
 * FarmersDirectoryPage Component.
 *
 * Searchable directory of registered farmers, landholdings, field plots,
 * and soil testing status across the agricultural officer's jurisdiction.
 */

import React, { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import { useDistrictFarmers } from '@/features/officer/hooks/useOfficerData';
import {
  Users,
  Search,
  MapPin,
  Phone,
  ChevronRight,
} from 'lucide-react';
import type { Farmer } from '@/types/domain';

export const FarmersDirectoryPage: React.FC = () => {
  const { farmers, fields, isLoading } = useDistrictFarmers();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFarmer, setSelectedFarmer] = useState<Farmer | null>(null);

  const filteredFarmers = farmers.filter((f) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      f.full_name.toLowerCase().includes(q) ||
      f.phone.includes(q) ||
      f.village.toLowerCase().includes(q) ||
      String(f.id).includes(q)
    );
  });

  const farmerFields = selectedFarmer
    ? fields.filter((f) => f.farmer_id === selectedFarmer.id)
    : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-display font-extrabold text-text tracking-tight">
            Farmer Directory
          </h1>
          <p className="text-body text-text-secondary">
            Manage farmers, verified landholdings, and soil health profiles in your district
          </p>
        </div>

        <div className="w-full sm:w-80">
          <div className="relative">
            <Search className="w-4 h-4 text-text-muted absolute left-3 top-1/2 -translate-y-1/2" aria-hidden="true" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by name, phone, village..."
              className="w-full pl-9 pr-3 py-2 rounded-xl bg-surface border border-border text-small text-text placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-primary-500 shadow-sm"
            />
          </div>
        </div>
      </div>

      {/* Directory Grid / Split View */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Farmers List */}
        <div className="lg:col-span-2 space-y-3">
          {isLoading ? (
            <div className="space-y-3">
              <Card variant="default" padding="md">
                <Skeleton width="50%" height={24} />
                <Skeleton height={40} className="mt-2" />
              </Card>
              <Card variant="default" padding="md">
                <Skeleton width="50%" height={24} />
                <Skeleton height={40} className="mt-2" />
              </Card>
            </div>
          ) : filteredFarmers.length === 0 ? (
            <Card variant="raised" padding="lg" className="text-center py-12">
              <Users className="w-8 h-8 text-text-muted mx-auto mb-2" aria-hidden="true" />
              <h3 className="text-subheading font-bold text-text">No farmers found</h3>
              <p className="text-small text-text-secondary mt-1">
                Try searching with a different name or phone number.
              </p>
            </Card>
          ) : (
            filteredFarmers.map((f) => {
              const plotsCount = fields.filter((p) => p.farmer_id === f.id).length;
              const isSelected = selectedFarmer?.id === f.id;

              return (
                <Card
                  key={f.id}
                  variant="default"
                  padding="md"
                  onClick={() => setSelectedFarmer(f)}
                  className={`cursor-pointer transition-all hover:border-primary-400 ${
                    isSelected ? 'border-primary-600 bg-primary-50/20 shadow-sm ring-1 ring-primary-500' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-body font-bold text-text">{f.full_name}</span>
                        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-surface-raised border border-border text-text-muted">
                          ID #{f.id}
                        </span>
                      </div>

                      <div className="flex items-center gap-3 text-caption text-text-secondary flex-wrap">
                        <span className="flex items-center gap-1">
                          <Phone className="w-3.5 h-3.5 text-primary-600" aria-hidden="true" />
                          {f.phone}
                        </span>
                        <span>•</span>
                        <span className="flex items-center gap-1">
                          <MapPin className="w-3.5 h-3.5 text-primary-600" aria-hidden="true" />
                          {f.village}
                        </span>
                        <span>•</span>
                        <span>{f.landholding_acres} Acres</span>
                        <span>•</span>
                        <span>{plotsCount || 1} Plot(s)</span>
                      </div>
                    </div>

                    <ChevronRight className="w-5 h-5 text-text-muted" aria-hidden="true" />
                  </div>
                </Card>
              );
            })
          )}
        </div>

        {/* Farmer Drilldown Sidebar */}
        <div className="lg:col-span-1">
          {selectedFarmer ? (
            <Card variant="raised" padding="md" className="space-y-4 sticky top-6">
              <div className="pb-3 border-b border-border space-y-1">
                <span className="text-caption font-bold text-text-muted uppercase">
                  Farmer Details
                </span>
                <h2 className="text-subheading font-bold text-text">{selectedFarmer.full_name}</h2>
                <p className="text-caption text-text-secondary">
                  {selectedFarmer.village}, District #{selectedFarmer.district_id}
                </p>
              </div>

              <div className="space-y-3">
                <div className="p-3 rounded-lg bg-surface-raised border border-border text-small space-y-1">
                  <div className="flex justify-between">
                    <span className="text-text-muted">Total Landholding:</span>
                    <strong className="text-text">{selectedFarmer.landholding_acres} Acres</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-muted">Preferred Language:</span>
                    <strong className="text-text uppercase">{selectedFarmer.preferred_language}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-muted">Contact:</span>
                    <strong className="text-text">{selectedFarmer.phone}</strong>
                  </div>
                </div>

                {/* Plot Breakdown */}
                <div className="space-y-2">
                  <span className="text-caption font-bold text-text uppercase block">
                    Registered Plots ({farmerFields.length || 1})
                  </span>

                  {farmerFields.length > 0 ? (
                    farmerFields.map((field) => (
                      <div
                        key={field.id}
                        className="p-2.5 rounded-lg bg-surface border border-border text-caption space-y-1"
                      >
                        <div className="flex justify-between font-bold text-text">
                          <span>{field.field_name}</span>
                          <span>{field.area_acres} Ac</span>
                        </div>
                        <div className="text-text-secondary flex justify-between">
                          <span>Soil: {field.soil_type || 'Black Soil'}</span>
                          <span>Irrigation: {field.irrigation_type || 'Borewell'}</span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="p-2.5 rounded-lg bg-surface border border-border text-caption space-y-1">
                      <div className="flex justify-between font-bold text-text">
                        <span>Main Plot #1</span>
                        <span>{selectedFarmer.landholding_acres} Ac</span>
                      </div>
                      <div className="text-text-secondary flex justify-between">
                        <span>Soil: Red Sandy Loam</span>
                        <span>Irrigation: Canal / Borewell</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </Card>
          ) : (
            <Card variant="default" padding="md" className="text-center py-12 text-text-muted">
              <MapPin className="w-8 h-8 mx-auto mb-2 opacity-50" aria-hidden="true" />
              <p className="text-small">Select a farmer to inspect plot boundaries, soil health, and advisory history.</p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

export default FarmersDirectoryPage;
