/**
 * Farmer & Farm Management API Service.
 *
 * Interacts with:
 * - GET /api/v1/farmers
 * - GET /api/v1/farmers/{id}
 * - GET /api/v1/fields
 * - GET /api/v1/fields/{id}
 * - GET /api/v1/crops
 * - GET /api/v1/field-crops
 * - GET /api/v1/soil-samples
 */

import { apiClient } from '@/services/api/client';
import type { Farmer, Field, Crop, FieldCrop, SoilSample } from '@/types/domain';

export const farmerApi = {
  /** List all farmers (or lookup for current context). */
  async listFarmers(): Promise<Farmer[]> {
    return apiClient.get<Farmer[]>('/farmers');
  },

  /** Get a farmer profile by ID. */
  async getFarmerById(id: number): Promise<Farmer> {
    return apiClient.get<Farmer>(`/farmers/${id}`);
  },

  /** Get all fields belonging to farmers. */
  async listFields(): Promise<Field[]> {
    return apiClient.get<Field[]>('/fields');
  },

  /** Get a field by ID. */
  async getFieldById(id: number): Promise<Field> {
    return apiClient.get<Field>(`/fields/${id}`);
  },

  /** Get crop catalog. */
  async listCrops(): Promise<Crop[]> {
    return apiClient.get<Crop[]>('/crops');
  },

  /** Get crop plantings / field crops. */
  async listFieldCrops(): Promise<FieldCrop[]> {
    return apiClient.get<FieldCrop[]>('/field-crops');
  },

  /** Get soil samples. */
  async listSoilSamples(): Promise<SoilSample[]> {
    return apiClient.get<SoilSample[]>('/soil-samples');
  },
};
