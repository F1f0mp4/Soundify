"""Domain-specific library modules.

Modules here import soundify domain models and provide higher-level logic
(matching, playlist generation, etc.). Pure utilities that don't depend
on domain models live in ``soundify.utils`` instead.

Consumers should import directly from submodules::

    from soundify.lib.matching import find_best_album_match
    from soundify.lib.m3u import write_m3u
"""
