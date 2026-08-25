/**
 * Vision Intelligence API Service.
 *
 * Interacts with:
 * - POST /api/v1/vision/images (Multipart image file upload + metadata)
 * - GET /api/v1/vision/analyses/{uuid}
 * - GET /api/v1/vision/analyses
 */

import { apiClient } from '@/services/api/client';
import type {
  ImageUploadRequest,
  ImageUploadResponse,
  AnalysisResponse,
  AnalysisListResponse,
} from '@/types/vision';

export const visionApi = {
  /** Upload crop image and trigger background vision pipeline. */
  async uploadImage(
    file: File | Blob,
    filename: string = 'crop_image.jpg',
    metadata: ImageUploadRequest = {},
  ): Promise<ImageUploadResponse> {
    const formData = new FormData();
    formData.append('file', file, filename);
    formData.append('metadata', JSON.stringify(metadata));

    return apiClient.postForm<ImageUploadResponse>('/vision/images', formData);
  },

  /** Get detailed analysis result by UUID. */
  async getAnalysis(analysisUuid: string): Promise<AnalysisResponse> {
    return apiClient.get<AnalysisResponse>(`/vision/analyses/${analysisUuid}`);
  },

  /** List farmer image analyses. */
  async listAnalyses(offset: number = 0, limit: number = 20): Promise<AnalysisListResponse> {
    return apiClient.get<AnalysisListResponse>(`/vision/analyses?offset=${offset}&limit=${limit}`);
  },
};
