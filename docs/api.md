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

## How to make your own API Key

### Create a Google Studio API key

1. Go to [https://aistudio.google.com/](https://aistudio.google.com/)
2. Make a new account.
3. Go to API Keys above your account, and create a new API key. This is now an upaid tier; you can see your allowed models and uses under Rate Limit.

   ! Be careful to never share your API KEY anywhere! Always keep an eye on usage, especially if you ever use a paid tier!

### Adding your key locally

1. Find the folder below that you created during installation.

        `Users/your_user_name/workspace/projects`

2. Create a txt file called: *GeminiKey.txt*

3. Inside the file, simply paste your key. Your Grasshopper files should now be able to find your key.
