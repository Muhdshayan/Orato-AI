"""
Content Relevance – Package Init
==================================
Re-exports the singleton service for convenient imports::

    from python_modules.content_relevance import content_relevance_service
"""
import os

# Skip service import when running standalone (e.g. test_content_relevance.py)
# to avoid pulling in app.core.database and backend deps.
if __name__ != "__main__" and os.getenv("CR_STANDALONE") != "1":
    from python_modules.content_relevance.content_relevance_service import (  # noqa: F401
        content_relevance_service,
    )
