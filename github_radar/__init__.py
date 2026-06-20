"""github-radar — a feed of popular / AI-related GitHub repositories.

github-radar aggregates trending and high-signal repositories from several
sources (the official GitHub Search API, GitHub Trending, and optional extras),
deduplicates them by ``full_name``, scores them with a momentum-aware ranking,
and emits the result as JSON, a Markdown digest, or an Atom feed.

The package is intentionally dependency-light: everything ships on the Python
standard library (``urllib``, ``json``, ``html.parser``, ``xml``). See
``README.md`` for the pitch, sources table, and ranking explanation.
"""

from .models import Repo

__all__ = ["Repo", "__version__"]
__version__ = "0.1.0"
