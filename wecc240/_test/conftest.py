"""Shared test setup

Set `WECC240_CACHEDIR` to keep downloaded data in a folder other than the
`cache` package default (inside site-packages, so lost on every fresh
install, e.g., in CI). wecc240 itself does not cache anything yet; this is
here so tests that use sibling packages (e.g. `loads`) honor it.
"""

import os

if os.environ.get("WECC240_CACHEDIR"):
    from cache import Cache # pylint: disable=import-error
    Cache.CACHEDIR = os.environ["WECC240_CACHEDIR"]
