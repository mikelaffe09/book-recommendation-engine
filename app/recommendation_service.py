import math
import os
from numbers import Number
from typing import Any, Dict, List

from dotenv import load_dotenv
from supabase import Client, create_client

from app.recommender import recommend_books_for_user


Recommendation = Dict[str, Any]


def get_required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value


def get_supabase_client() -> Client:
    load_dotenv()

    supabase_url = get_required_env("SUPABASE_URL")
    supabase_key = get_required_env("SUPABASE_KEY")

    return create_client(supabase_url, supabase_key)


def clean_for_supabase(value: Any) -> Any:
    """
    Supabase/PostgREST does not accept NaN or Infinity in JSON payloads.
    Pandas often creates NaN for empty database fields, so we convert those to None.
    """
    if value is None:
        return None

    if isinstance(value, Number):
        try:
            if math.isnan(float(value)) or math.isinf(float(value)):
                return None
        except (TypeError, ValueError):
            return None

        return value

    if isinstance(value, dict):
        return {
            key: clean_for_supabase(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            clean_for_supabase(item)
            for item in value
        ]

    if isinstance(value, str):
        stripped = value.strip()

        if stripped.lower() in {"nan", "none", "null"}:
            return None

        return stripped

    return value


def build_recommendation_rows(
    user_id: str,
    recommendations: List[Recommendation],
    recommendation_type: str = "personalized"
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for recommendation in recommendations:
        catalogue_book_id = recommendation.get("id")

        if not catalogue_book_id:
            continue

        row = {
            "user_id": user_id,
            "catalogue_book_id": str(catalogue_book_id),
            "title": recommendation.get("title") or "Untitled",
            "author": recommendation.get("author"),
            "cover_url": recommendation.get("cover_url"),
            "genre": recommendation.get("genre"),
            "isbn": recommendation.get("isbn"),
            "score": recommendation.get("score") or 0,
            "reason": recommendation.get("reason"),
            "recommendation_type": recommendation_type,
            "metadata": {
                "published_year": recommendation.get("published_year"),
                "publisher": recommendation.get("publisher"),
                "series": recommendation.get("series"),
                "total_pages": recommendation.get("total_pages"),
                "positive_similarity": recommendation.get("positive_similarity"),
                "negative_similarity": recommendation.get("negative_similarity"),
                "genre_bonus": recommendation.get("genre_bonus"),
            },
        }

        rows.append(clean_for_supabase(row))

    return rows


def clear_existing_recommendations(
    supabase: Client,
    user_id: str,
    recommendation_type: str
) -> None:
    table_name = os.getenv("SUPABASE_RECOMMENDATIONS_TABLE", "book_recommendations")

    (
        supabase
        .table(table_name)
        .delete()
        .eq("user_id", user_id)
        .eq("recommendation_type", recommendation_type)
        .execute()
    )


def insert_recommendations(
    supabase: Client,
    rows: List[Dict[str, Any]]
) -> None:
    if not rows:
        print("No recommendation rows to insert.")
        return

    table_name = os.getenv("SUPABASE_RECOMMENDATIONS_TABLE", "book_recommendations")

    (
        supabase
        .table(table_name)
        .insert(rows)
        .execute()
    )


def generate_and_save_recommendations_for_user(
    user_id: str,
    limit: int = 10,
    recommendation_type: str = "personalized"
) -> List[Recommendation]:
    print("Generating personalized recommendations...")
    recommendations = recommend_books_for_user(user_id=user_id, limit=limit)

    print(f"Generated {len(recommendations)} recommendations.")

    rows = build_recommendation_rows(
        user_id=user_id,
        recommendations=recommendations,
        recommendation_type=recommendation_type
    )

    supabase = get_supabase_client()

    print("Clearing old recommendations for this user...")
    clear_existing_recommendations(
        supabase=supabase,
        user_id=user_id,
        recommendation_type=recommendation_type
    )

    print("Saving new recommendations...")
    insert_recommendations(
        supabase=supabase,
        rows=rows
    )

    print("Done. Recommendations saved to Supabase.")

    return recommendations


def main():
    print("Book Recommendation Generator")
    print("------------------------------------")

    user_id = input("Paste Supabase user_id: ").strip()

    if not user_id:
        print("No user_id provided. Exiting.")
        return

    limit_input = input("How many recommendations? Default is 10: ").strip()

    try:
        limit = int(limit_input) if limit_input else 10
    except ValueError:
        print("Invalid number. Using default limit of 10.")
        limit = 10

    try:
        recommendations = generate_and_save_recommendations_for_user(
            user_id=user_id,
            limit=limit,
            recommendation_type="personalized"
        )

        print("\nSaved recommendations:\n")

        for index, recommendation in enumerate(recommendations, start=1):
            print(f"{index}. {recommendation.get('title')} — {recommendation.get('author')}")
            print(f"   Score: {recommendation.get('score')}")
            print(f"   Reason: {recommendation.get('reason')}")
            print()

    except Exception as error:
        print("\nSomething went wrong:")
        print(error)


if __name__ == "__main__":
    main()