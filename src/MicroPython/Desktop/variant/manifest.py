# Desktop shell and firmware-side Python code live in host read-only storage,
# analogous to frozen firmware modules. Never freeze apps_unfrozen or assets:
# game bytecode, state, native buffers and SD records still consume the heap.
freeze(".", "sim_build.py", opt=0)
freeze("../..", "picoware", opt=0)
freeze("../../../../simulator", "run.py", opt=0)
freeze("../../../../simulator/hardware", opt=0)
