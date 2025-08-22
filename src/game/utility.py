from collections import defaultdict
from typing import Dict, Set

def generate_valid_source_references(sources) -> Dict[str, str]:

    # Build shortforms
    valid_shortforms: Dict[str, Set[str]] = defaultdict(set)
    for source in sources:
        words = source.split()
        if not words:
            continue

        # Initials in mixed, lower, and upper case
        initials = "".join(word[0] for word in words)
        valid_shortforms[source].update(
            {initials, initials.lower(), initials.upper()}
        )

        # First word logic (skip "a" or "the")
        first_word_index = (
            1 if words[0].lower() in {"a", "the"} and len(words) > 1 else 0
        )
        first_word = words[first_word_index]
        valid_shortforms[source].update(
            {first_word, first_word.lower(), first_word.upper()}
        )

    # Uniqueness check
    shortform_to_sources = defaultdict(list)
    for source, shortforms in valid_shortforms.items():
        for sf in shortforms:
            shortform_to_sources[sf].append(source)

    # Keep only unique mappings
    shortform_mapping = {
        sf: srcs[0] for sf, srcs in shortform_to_sources.items() if len(srcs) == 1
    }

    # Always map full sources to themselves
    shortform_mapping.update({src: src for src in sources})

    return shortform_mapping
