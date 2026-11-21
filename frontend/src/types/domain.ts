/**
 * Domain entity types matching the backend Pydantic response schemas.
 *
 * See: backend/app/schemas/farmer.py, officer.py, field.py, crop.py, district.py, etc.
 *
 * These types represent the JSON shapes returned by the REST API.
 * Fields use snake_case to match the backend exactly.
 */

// ── District ─────────────────────────────────────────────────────────────────

export interface District {
  id: number;
  name: string;
  state: string;
  agro_climatic_zone: string | null;
  created_at: string;
  updated_at: string;
}

// ── Farmer ───────────────────────────────────────────────────────────────────

export interface Farmer {
  id: number;
  farmer_code: string; // UUID
  full_name: string;
  phone: string;
  preferred_language: string;
  district_id: number;
  village: string;
  landholding_acres: number;
  created_at: string;
  updated_at: string;
}

export interface FarmerCreate {
  full_name: string;
  phone: string;
  preferred_language: string;
  district_id: number;
  village: string;
  landholding_acres: number;
}

export interface FarmerUpdate {
  full_name?: string;
  phone?: string;
  preferred_language?: string;
  district_id?: number;
  village?: string;
  landholding_acres?: number;
}

// ── Officer ──────────────────────────────────────────────────────────────────

export interface Officer {
  id: number;
  officer_code: string; // UUID
  full_name: string;
  phone: string;
  email: string | null;
  designation: string;
  district_id: number;
  created_at: string;
  updated_at: string;
}

// ── Field ────────────────────────────────────────────────────────────────────

export interface Field {
  id: number;
  farmer_id: number;
  field_name: string;
  area_acres: number;
  latitude: number | null;
  longitude: number | null;
  soil_type: string | null;
  irrigation_type: string | null;
  created_at: string;
  updated_at: string;
}

// ── Crop ─────────────────────────────────────────────────────────────────────

export interface Crop {
  id: number;
  name?: string;
  crop_name: string;
  scientific_name: string | null;
  season: string;
  duration_days?: number;
  created_at: string;
  updated_at: string;
}

// ── Field Crop ───────────────────────────────────────────────────────────────

export interface FieldCrop {
  id: number;
  field_id: number;
  crop_id: number;
  season: string;
  year: number;
  sowing_date: string | null;
  harvest_date: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

// ── Soil Sample ──────────────────────────────────────────────────────────────

// Matches the backend SoilSampleResponse: when and where a sample was taken and where it is in
// the lab process. Test values (pH, N, P, K) are not stored by the backend yet.
export type SoilSampleStatus = 'Collected' | 'In Transit' | 'Testing' | 'Completed' | 'Delivered';

export interface SoilSample {
  sample_id: number;
  sample_uuid: string;
  farmer_id: number;
  field_id: number;
  collector_id: number | null;
  collection_date: string;
  latitude: number | null;
  longitude: number | null;
  status: SoilSampleStatus;
  created_at: string;
  updated_at: string;
}
