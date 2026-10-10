# Run log — OBS_2006 (plan p06)

- Software: HEC-RAS 7.0.1 (June 2026 build per computation log), Windows 11.
- Plan: `OBS_2006` (`Ukai_Lower_Tapi_A2.p06`), geometry `g01`, unsteady flow `OBS2006` (`u07`).
- Window: 2006-08-06 00:00 to 2006-08-11 18:00 (138 h).
- Computation interval 10 s; hydrograph output 15 min; mapping output 1 h; 2D equation set diffusion wave; Manning n 0.04 uniform; cells 96,962.
- Boundaries: upstream flow hydrograph (hourly, energy slope 0.005); downstream normal depth (slope 0.0005).
- Result: finished, runtime 1 h 05 min, overall volume accounting error 0.0004% (read from the on-screen summary on 2026-10-06; no log file saved).
- Exports from RAS Mapper (OBS2006 folder): max depth, max velocity, max WSE, arrival time (0.1 m, hours). Copied unchanged into `assets/`; extent derived by script.
- Not captured: warnings list, per-time-step iteration counts.
