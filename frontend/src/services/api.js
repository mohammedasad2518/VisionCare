/**
 * VisionCare Centralized API Service
 * Manages communication between React frontend and FastAPI backend.
 */

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');

/**
 * Standardized client-safe API error wrapper
 */
export class ApiError extends Error {
  constructor(message, status = 0, detail = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Fetches JSON with standardized error parsing and timeout protection
 */
async function fetchWithTimeout(resource, options = {}, timeoutMs = 30000) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(resource, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(id);
    return response;
  } catch (error) {
    clearTimeout(id);
    if (error.name === 'AbortError') {
      throw new ApiError('The screening request timed out after 30 seconds. Please try again.', 408);
    }
    throw new ApiError('Unable to connect to the VisionCare service. Please check that the server is active.', 0);
  }
}

/**
 * Parses response body safely without leaking raw stack traces
 */
async function parseResponseBody(response) {
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    try {
      return await response.json();
    } catch {
      return null;
    }
  }
  return null;
}

/**
 * Check backend operational health and model readiness
 * @returns {Promise<{ available: boolean, status: string, architecture?: string, error?: string }>}
 */
export async function checkHealth() {
  try {
    const response = await fetchWithTimeout(`${API_BASE_URL}/api/health`, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
    }, 5000);

    const data = await parseResponseBody(response);

    if (!response.ok) {
      return {
        available: false,
        status: 'unavailable',
        error: data?.detail || `HTTP error ${response.status}`,
      };
    }

    const modelInfo = data?.model || {};
    return {
      available: Boolean(modelInfo.available),
      status: data?.status || 'unknown',
      appName: data?.app_name || 'VisionCare API',
      version: data?.version || '1.0.0',
      architecture: modelInfo.architecture || 'VGG19 (Transfer Learning)',
      categories: modelInfo.categories || ['Cataract', 'Diabetic Retinopathy', 'Glaucoma', 'Normal'],
      error: modelInfo.error || null,
    };
  } catch (err) {
    return {
      available: false,
      status: 'offline',
      error: err.message || 'Connection failed',
    };
  }
}

/**
 * Submits a retinal fundus image for model evaluation
 * @param {File} file - Retinal photograph file (JPG, JPEG, or PNG)
 * @returns {Promise<{ prediction: string, confidence: number, scores: Record<string, number>, image: object, screening_id?: number }>}
 */
export async function predictImage(file) {
  if (!file) {
    throw new ApiError('No image file was provided for evaluation.', 400);
  }

  const formData = new FormData();
  formData.append('file', file);

  const response = await fetchWithTimeout(`${API_BASE_URL}/api/predict`, {
    method: 'POST',
    body: formData,
  }, 45000);

  const data = await parseResponseBody(response);

  if (!response.ok) {
    let errorMessage = 'An error occurred during image screening.';
    if (data?.detail) {
      errorMessage = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    } else if (response.status === 503) {
      errorMessage = 'The screening service is currently unavailable. Model weights are not loaded.';
    } else if (response.status === 413) {
      errorMessage = 'The uploaded file exceeds the 10 MB size limit.';
    } else if (response.status === 400) {
      errorMessage = 'The uploaded file is invalid or could not be processed.';
    }
    throw new ApiError(errorMessage, response.status, data);
  }

  if (!data || data.status !== 'success') {
    throw new ApiError('Received an invalid or malformed screening response.', 500);
  }

  return {
    prediction: data.prediction,
    confidence: Number(data.confidence) || 0,
    screeningId: data.screening_id || null,
    scores: data.scores || data.probabilities || {},
    probabilities: data.probabilities || data.scores || {},
    image: data.image || {
      filename: file.name,
      size_bytes: file.size,
    },
    message: data.message || 'Image evaluated successfully.',
  };
}

/**
 * Requests Grad-CAM visual explanation for an evaluated retinal photograph
 * @param {File} file - Retinal photograph file (JPG, JPEG, or PNG)
 * @param {number|null} classIndex - Optional target class index (0-3)
 * @returns {Promise<{ prediction: string, classIndex: number, confidence: number, targetLayer: string, heatmapDataUrl: string, overlayDataUrl: string, originalDimensions: [number, number], scores: Record<string, number> }>}
 */
export async function generateGradCAM(file, classIndex = null) {
  if (!file) {
    throw new ApiError('No image file was provided for Grad-CAM visualization.', 400);
  }

  const formData = new FormData();
  formData.append('file', file);

  let url = `${API_BASE_URL}/api/gradcam`;
  if (classIndex !== null && classIndex !== undefined) {
    url += `?class_index=${encodeURIComponent(classIndex)}`;
  }

  const response = await fetchWithTimeout(url, {
    method: 'POST',
    body: formData,
  }, 45000);

  const data = await parseResponseBody(response);

  if (!response.ok) {
    let errorMessage = 'An error occurred while generating the visual explanation.';
    if (data?.detail) {
      errorMessage = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    } else if (response.status === 503) {
      errorMessage = 'The visualization service is temporarily unavailable. Model weights are not loaded.';
    } else if (response.status === 400) {
      errorMessage = 'The uploaded file or target category is invalid.';
    }
    throw new ApiError(errorMessage, response.status, data);
  }

  if (!data || data.status !== 'success') {
    throw new ApiError('Received an invalid or malformed visual explanation response.', 500);
  }

  return {
    prediction: data.prediction,
    classIndex: data.class_index,
    confidence: Number(data.confidence) || 0,
    targetLayer: data.target_layer || 'block5_conv4',
    heatmapDataUrl: data.heatmap_data_url,
    overlayDataUrl: data.overlay_data_url,
    originalDimensions: data.original_dimensions,
    scores: data.scores || {},
    message: data.message || 'Grad-CAM visual explanation generated successfully.',
  };
}

/**
 * Retrieves archived screening records from the local SQLite database
 * @param {object} params - Query filters { skip: number, limit: number, category: string }
 * @returns {Promise<{ status: string, totalCount: number, records: Array }>}
 */
export async function fetchHistory({ skip = 0, limit = 50, category = null } = {}) {
  let url = `${API_BASE_URL}/api/history?skip=${encodeURIComponent(skip)}&limit=${encodeURIComponent(limit)}`;
  if (category && category !== 'All') {
    url += `&category=${encodeURIComponent(category)}`;
  }

  const response = await fetchWithTimeout(url, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
  }, 10000);

  const data = await parseResponseBody(response);

  if (!response.ok) {
    throw new ApiError(data?.detail || 'Failed to retrieve screening history.', response.status, data);
  }

  return {
    status: data?.status || 'success',
    totalCount: data?.total_count || 0,
    records: Array.isArray(data?.records) ? data.records : [],
  };
}

/**
 * Retrieves full details of a specific screening record
 * @param {number} screeningId - Unique record ID
 * @returns {Promise<object>}
 */
export async function fetchHistoryRecord(screeningId) {
  const response = await fetchWithTimeout(`${API_BASE_URL}/api/history/${encodeURIComponent(screeningId)}`, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
  }, 10000);

  const data = await parseResponseBody(response);

  if (!response.ok) {
    throw new ApiError(data?.detail || `Screening record ID ${screeningId} not found.`, response.status, data);
  }

  return data;
}

/**
 * Deletes an individual screening record from the database
 * @param {number} screeningId - Unique record ID
 * @returns {Promise<{ status: string, message: string, deletedId: number }>}
 */
export async function deleteHistoryRecord(screeningId) {
  const response = await fetchWithTimeout(`${API_BASE_URL}/api/history/${encodeURIComponent(screeningId)}`, {
    method: 'DELETE',
    headers: {
      Accept: 'application/json',
    },
  }, 10000);

  const data = await parseResponseBody(response);

  if (!response.ok) {
    throw new ApiError(data?.detail || `Failed to delete record ID ${screeningId}.`, response.status, data);
  }

  return data;
}

/**
 * Permanently clears all screening history records from the database
 * @returns {Promise<{ status: string, message: string, deletedCount: number }>}
 */
export async function clearAllHistory() {
  const response = await fetchWithTimeout(`${API_BASE_URL}/api/history`, {
    method: 'DELETE',
    headers: {
      Accept: 'application/json',
    },
  }, 10000);

  const data = await parseResponseBody(response);

  if (!response.ok) {
    throw new ApiError(data?.detail || 'Failed to clear screening history.', response.status, data);
  }

  return data;
}

export default {
  checkHealth,
  predictImage,
  generateGradCAM,
  fetchHistory,
  fetchHistoryRecord,
  deleteHistoryRecord,
  clearAllHistory,
  API_BASE_URL,
};
