ROAD INTELLIGENCE WEBSITE

1. Install Node.js (LTS).
2. Open terminal in this folder.
3. Run:
   npm install
4. Run:
   npm run dev
5. Open the localhost URL shown by Vite.

The dashboard expects the backend at:
http://127.0.0.1:8000

Backend API:
GET  /api/dashboard/stats
GET  /api/damages
PATCH /api/damages/{id}/status
