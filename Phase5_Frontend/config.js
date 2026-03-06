// Phase 5 — API base URL for POST /chat
// When served from same server (run_server.sh), use same origin. Else default to localhost:8000
window.MF_FAQ_API_BASE = window.MF_FAQ_API_BASE || (typeof window !== 'undefined' && window.location && window.location.origin ? window.location.origin : 'http://localhost:8000');
