"""
stbv_bench/
===========
STBV-Bench: a reproducible benchmark of Semantic Trust Boundary Violation
(STBV) attacks, built by injecting seeded, parameterized semantic
manipulations into REAL public-dataset V2X kinematics (VeReMi Extension),
via this repo's own message schema.

Pipeline (see BUILD_STBV_BENCH.md / stbv_bench/build_stbv_bench.py):

    Standard Public Dataset (VeReMi Extension, real kinematics)
        -> Canonical Message Representation (stbv_bench.canonical)
        -> Semantic Transformation Engine (stbv_bench.transformations)
        -> Semantic Validation (structural/behavioral plausibility check)
        -> STBV Attack Injection (payload written into scene_context)
        -> Benchmark Validation (schema + metadata completeness check)
        -> Final STBV-Bench (data/stbv_bench/<version>/)

This module does NOT relabel existing VeReMi kinematic attacks as STBV
attacks -- VeReMi's own ground truth (is_attacker) is preserved unchanged as
provenance metadata, but STBV-Bench's own attack/benign labels come
exclusively from whether a semantic transformation was applied to that
message, not from VeReMi's kinematic ground truth.
"""
