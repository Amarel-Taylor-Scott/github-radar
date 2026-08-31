"""github-radar: momentum-aware GitHub and agent-ecosystem discovery.

The package provides a general repository feed plus reusable engines for agent
extension catalogs and domain-specific Project Radar publications. Collection
is read-only and the core runtime uses only the Python standard library.
"""

from .models import Repo

__all__ = ["Repo", "__version__"]
__version__ = "0.2.0"
