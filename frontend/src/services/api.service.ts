/**
 * Base API Service
 *
 * Wrapper around fetch API with error handling and JSON parsing
 */

import { API_BASE_URL } from '@config/api.config';

/**
 * API Error class for better error handling
 */
export class APIError extends Error {
  status: number;
  detail: string;
  response?: Response;

  constructor(status: number, detail: string, response?: Response) {
    super(detail);
    this.name = 'APIError';
    this.status = status;
    this.detail = detail;
    this.response = response;
  }
}

/**
 * Base fetch wrapper with error handling
 */
export const apiFetch = async <T = any>(
  path: string,
  options?: RequestInit
): Promise<T> => {
  const url = `${API_BASE_URL}${path}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...(options?.body instanceof FormData
          ? {}
          : { 'Content-Type': 'application/json' }),
        ...options?.headers,
      },
    });

    if (!response.ok) {
      let detail = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const errorData = await response.json();
        detail = errorData.detail || detail;
      } catch {
        // Ignore JSON parse errors
      }
      throw new APIError(response.status, detail, response);
    }

    // Return response for file downloads
    if (options?.headers && 'Accept' in (options.headers as Record<string, string>)) {
      return response as T;
    }

    return await response.json();
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new Error(`Network error: ${(error as Error).message}`);
  }
};

/**
 * GET request
 */
export const apiGet = <T = any>(path: string, options?: RequestInit): Promise<T> =>
  apiFetch<T>(path, { ...options, method: 'GET' });

/**
 * POST request
 */
export const apiPost = <T = any>(
  path: string,
  body?: any,
  options?: RequestInit
): Promise<T> =>
  apiFetch<T>(path, {
    ...options,
    method: 'POST',
    body: body instanceof FormData ? body : JSON.stringify(body),
  });

/**
 * DELETE request
 */
export const apiDelete = <T = any>(path: string, options?: RequestInit): Promise<T> =>
  apiFetch<T>(path, { ...options, method: 'DELETE' });
