# EndoScan Java Stats Service

This service keeps the statistics module separate from the Python FastAPI core.
Python renders the pages and proxies requests to this Java HTTP API.

## Run

```powershell
cd D:\Endos\v3\java_stats_service
.\run.ps1
```

Default URL:

```text
http://127.0.0.1:8081
```

Available endpoints:

```text
GET /health
GET /api/stats/admin/dashboard
GET /api/stats/admin/users
GET /api/stats/admin/analyses
GET /api/stats/admin/review-queue
GET /api/stats/admin/dataset
GET /api/stats/admin/model-stats
GET /api/stats/admin/reports
GET /api/stats/admin/news-manager
GET /api/stats/admin/activity-logs
GET /api/stats/admin/messages
GET /api/stats/admin/settings
GET /api/stats/admin/user-detail
GET /api/stats/admin/analysis-detail

GET /api/stats/user/snapshot
GET /api/stats/user/scan-library
GET /api/stats/user/ai-insights
GET /api/stats/user/risk-map
GET /api/stats/user/confidence-pulse
GET /api/stats/user/timeline
GET /api/stats/user/reports
GET /api/stats/user/profile
GET /api/stats/user/analysis-detail
```

If you need a different port:

```powershell
$env:PORT = "8082"
.\run.ps1
```

Then run Python with:

```powershell
$env:JAVA_STATS_BASE_URL = "http://127.0.0.1:8082"
fastapi dev main.py
```
