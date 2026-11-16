from pydantic import BaseModel, Field

import logging
logger = logging.getLogger(__name__)


class UserQuery(BaseModel):
    """Validated user research query."""
    query: str = Field(min_length=5, max_length=2000)


def validate_user_query(query: str) -> UserQuery:
    """
    Validate and normalize an incoming research query.

    Args:
        query: User's natural-language research question.

    Returns:
        Validated UserQuery.

    Raises:
        ValueError: If the query is empty or outside allowed length.
    """

    query = query.strip()

    if not query:
        logger.warning("Input query rejected: empty query")
        raise ValueError("Research query must not be empty.")

    return UserQuery(query=query)