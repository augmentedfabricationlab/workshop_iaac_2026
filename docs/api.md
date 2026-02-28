---
layout: page
title: API Keys
---

# API Keys

## 10 Sacred Rules for Rhino Grasshopper API Calls

1. Never embed API keys in GH files, scripts, screenshots, or recordings  
2. One person, one key. No shared master keys  
3. Never commit secrets. Gitignore key files and run a secret scanner  
4. Enforce hard daily and monthly spend caps per key  
5. Rate limit, use backoff, and cap retries. No infinite loops  
6. Cache static data in sc.sticky to avoid repeat calls  
7. Only call the API on an explicit button press, not on recompute  
8. Downscale and compress images. Send the minimum views needed  
9. Log timestamps, model, input size, output size. Never log keys  
10. Fail closed on missing key, invalid key, or quota reached  