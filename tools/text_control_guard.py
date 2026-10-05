"""Prevent translation punctuation from introducing an ASCII-tilde command.

The game's rich-text measurement consumer treats '~' as a command introducer,
including when the following character is punctuation. A regex for known tags
alone therefore misses dangerous '~!' prose. This is a conservative source
invariant, not a complete grammar validator: existing ordered-tag checks and
consumer-specific validation are still required.
"""


def reject_new_ascii_tilde(source: str, target: str, slot: str = "text") -> None:
    if target.count("~") > source.count("~"):
        raise ValueError(
            f"{slot}: translation introduced ASCII '~'; this byte starts a game "
            "control command, including before punctuation"
        )
