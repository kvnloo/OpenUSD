#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Small dependency-free fuzzy scorer used by the command palette."""


def score(query, text):
    query = query.strip().lower()
    text = text.lower()
    if not query:
        return 1
    if text.startswith(query):
        return 10000 - len(text)

    index = text.find(query)
    if index >= 0:
        return 8000 - (index * 10) - len(text)

    q_index = 0
    previous = -2
    total = 0
    first = None
    for index, char in enumerate(text):
        if q_index >= len(query):
            break
        if char != query[q_index]:
            continue
        if first is None:
            first = index
        total += 20 if index == previous + 1 else 5
        previous = index
        q_index += 1

    if q_index != len(query):
        return None

    return 1000 + total - (first or 0) - len(text)


def ranked(query, items, key=lambda value: value, limit=50):
    matches = []
    for item in items:
        value = score(query, key(item))
        if value is not None:
            matches.append((value, item))
    matches.sort(key=lambda pair: (-pair[0], key(pair[1]).lower()))
    return [item for _, item in matches[:limit]]
