"""Backward-compatible entry point for the Terraria sprite composer."""

from TrueTerrariaGenerator import TerrariaCharacterGenerator, main

__all__ = ["TerrariaCharacterGenerator"]


if __name__ == "__main__":
    main()
