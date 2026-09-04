/**
 * Document API Service
 *
 * Handles agricultural knowledge-document uploads.
 *
 * Backend:
 * POST /api/v1/documents/upload
 */

import { apiClient } from '@/services/api/client';

export interface DocumentUploadMetadata {
  title?: string;
  crop?: string;
  state?: string;
  district?: string;
  season?: string;
  language?: string;
  document_type?: string;
}

export interface DocumentUploadResponse {
  id?: number;
  uuid?: string;
  title?: string;
  status?: string;
  message?: string;
  [key: string]: unknown;
}

export const documentsApi = {
  async upload(
    file: File,
    metadata: DocumentUploadMetadata = {},
  ): Promise<DocumentUploadResponse> {
    const formData =
      new FormData();

    formData.append(
      'file',
      file,
    );

    formData.append(
      'metadata',
      JSON.stringify({
        title:
          metadata.title ??
          file.name.replace(
            /\.[^/.]+$/,
            '',
          ),

        ...(metadata.crop
          ? {
              crop:
                metadata.crop,
            }
          : {}),

        ...(metadata.state
          ? {
              state:
                metadata.state,
            }
          : {}),

        ...(metadata.district
          ? {
              district:
                metadata.district,
            }
          : {}),

        ...(metadata.season
          ? {
              season:
                metadata.season,
            }
          : {}),

        language:
          metadata.language ??
          'en',

        document_type:
          metadata.document_type ??
          'agricultural_advisory',
      }),
    );

    return apiClient.postForm<DocumentUploadResponse>(
      '/documents/upload',
      formData,
    );
  },
};