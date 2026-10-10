# Run the fast solver on Windows (about 10 minutes of setup, then a few minutes per run)

Open the **MSYS2 UCRT64** window (Start menu) and run:

    cd /c/Ukai/Ukai/part_a_handoff/fast_solver      (use /e/Ukai/part_a_handoff/fast_solver if the project is on E:)
    gcc -O3 -march=native -fopenmp -shared -o li2d.dll li2d.c -lm
    ls li2d.dll

Then open a normal **Command Prompt** (Python 3.13 on PATH) in the same folder and run:

    python -m pip install numpy scipy tifffile opencv-python
    python multi.py 0.025

`multi.py` runs the 2006 replay and H01-H03 at Manning n = 0.025 and writes `multi_results_n0.025.json` and `res_*_n0.025.npz` here.
Compare the numbers with the HEC-RAS maps. Agreement is against HEC-RAS only, not against real observations.
