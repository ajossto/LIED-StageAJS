"""Générateur aléatoire isolé du moteur M4.

Le seul état aléatoire est une instance locale de ``random.Random(seed)``.
Cette petite façade fournit les trois tirages requis par le modèle sans toucher
au générateur global ni dépendre du RNG de NumPy.
"""
import math
import random


class ModelRNG:
    def __init__(self, seed: int):
        self._rng = random.Random(seed)

    def normal(self, mean: float, sd: float, size: int | None = None):
        if sd == 0.0:
            return mean if size is None else [mean] * size
        if size is None:
            return self._rng.gauss(mean, sd)
        return [self._rng.gauss(mean, sd) for _ in range(size)]

    def poisson(self, rate: float) -> int:
        """Tirage exact de Knuth, adapté aux taux démographiques M4 (<= 20)."""
        if rate < 0.0:
            raise ValueError("Poisson rate must be nonnegative")
        if rate == 0.0:
            return 0
        limit = math.exp(-rate)
        product = 1.0
        k = 0
        while product > limit:
            k += 1
            product *= self._rng.random()
        return k - 1

    def sample(self, population, k: int):
        return self._rng.sample(population, k)

    def randrange(self, stop: int) -> int:
        return self._rng.randrange(stop)

