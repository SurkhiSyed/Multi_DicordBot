// frontend_site/src/apiBase.js
const API_BASE =
  process.env.REACT_APP_API_URL || 'http://localhost:8000'; // dev fallback

export default API_BASE;
