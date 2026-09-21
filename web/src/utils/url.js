/**
 * Constructs the full URL for an avatar image based on its relative path.
 * Assumes the backend serves static files from the root of the API base URL + /uploads/
 * 
 * @param {string | null | undefined} relativePath The relative path from the backend (e.g., "2025-04-28/avatar.jpg")
 * @returns {string | null} The full URL or null if the path is invalid or base URL is missing.
 */
export function getAvatarUrl(relativePath) {
  // 1. Get the base URL from environment variables
  // Make sure VITE_API_BASE_URL is defined in your .env file (e.g., VITE_API_BASE_URL=http://localhost:8080)
  const baseUrl = import.meta.env.VITE_API_BASE_URL;

  // 2. Validate inputs
  if (!baseUrl) {
    console.warn('VITE_API_BASE_URL is not defined. Cannot construct avatar URL.');
    return null; // Or provide a default fallback if needed
  }
  if (!relativePath || typeof relativePath !== 'string' || relativePath.trim() === '') {
    return null; // Invalid or empty path
  }

  // 3. Construct the full URL
  // We assume the backend serves files directly under /api/uploads/ relative to the base URL
  // Based on user confirmation that /api prefix is needed for accessing static uploads
  const fullUrl = `/api/uploads/${relativePath.replace(/^\/+/, '')}`; // Add /api prefix and remove leading slashes from relative path

  return fullUrl;
} 