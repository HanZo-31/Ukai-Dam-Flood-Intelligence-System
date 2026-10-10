# Likely questions

- **Is this a new simulation?** No. The What-if page selects a stored HEC-RAS result (`computed: false`).
- **Is it validated or calibrated?** No. Every result is labelled uncalibrated and not scientifically validated.
- **What does "priority for review" mean?** An ordering of 5 km coordinate squares for people to check: newly flooded area first, then earlier arrival. Not an evacuation order or a recommended release.
- **Why are there no districts or population numbers?** No verified administrative or exposure data was supplied; those values show "not available".
- **What time is the timeline?** Elapsed model time from the start of the simulation window. The stored clock labels are nominal and their timezone is unverified.
- **Where is machine learning?** Disabled by the service: its acceptance gate needs two intermediate holdouts and only one exists.
- **What does the lookup time mean?** The service's time to validate and find stored data. Not model run time, not map drawing time.
- **What if the candidate service is down?** The What-if page says so; Explore, Compare and Evidence keep working.
