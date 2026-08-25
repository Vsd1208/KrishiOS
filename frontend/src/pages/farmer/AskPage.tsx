/**
 * AskPage.
 *
 * Dedicated page for the Ask KrishiOS AI Decision Support Assistant.
 */

import React from 'react';
import { AskKrishiOS } from '@/features/farmer/components/AskKrishiOS';
import { useFarmerProfile, useFarmerCrops } from '@/features/farmer/hooks/useFarmerData';

export const AskPage: React.FC = () => {
  const { data: farmer } = useFarmerProfile();
  const { fieldCrops } = useFarmerCrops();

  return (
    <div className="py-2">
      <AskKrishiOS farmer={farmer} fieldCrops={fieldCrops} />
    </div>
  );
};

export default AskPage;
