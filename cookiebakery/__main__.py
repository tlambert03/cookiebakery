"""Allow cookiebakery to be executable through `python -m cookiebakery`."""

from .cli import main

if __name__ == "__main__":  # pragma: no cover
    main()
