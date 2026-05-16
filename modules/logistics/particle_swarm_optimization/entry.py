"""Entry point for the Particle Swarm Optimization module.

Exposes ParticleSwarmOptimizationModule for the IIMP module loader.
"""
from modules.logistics.particle_swarm_optimization.module import (
    ParticleSwarmOptimizationModule,
)

__all__ = ["ParticleSwarmOptimizationModule"]
