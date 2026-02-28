---
layout: page
title: API Keys
---

## 10 Sacred Rules for Rhino Grasshopper API Calls

1. Never put API keys in GH files, scripts, panels, screenshots, or recordings.  
2. Use one key per person, never a shared master key.  
3. Never commit secrets to Git and always gitignore key files.  
4. Set hard daily and monthly spend limits per key.  
5. Rate limit requests and throttle bursts from sliders, timers, or trees.  
6. Use exponential backoff and a strict retry cap, never infinite retries.  
7. Cache identical results (e.g., via sc.sticky) to avoid duplicate calls.  
8. Trigger API calls only via an explicit button or “Run” toggle, not recompute.  
9. Send the smallest payload possible and downscale or crop images.  
10. Log timing, model, and sizes, but never log keys, and fail closed on errors.