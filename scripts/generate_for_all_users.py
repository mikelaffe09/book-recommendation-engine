import argparse
import os
import time
from typing import Any, Dict, List, Optional, Set

from dotenv import load_dotenv
from supabase import Client, create_client

from app.recommendation_service import generate_and_save_recommendations_for_user
from app.recommender import fetch_user_books


UserBookRow = Dict[str, Any]


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


def fetch_all_user_ids_from_books(page_size: int = 1000) -> List[str]:
    """
    Reads the books table and returns every unique user_id that has at least one book.
    This does not use auth.users because the recommender only cares about users who have books.
    """
    supabase = get_supabase_client()
    table_name = os.getenv("SUPABASE_USER_BOOKS_TABLE", "books")

    user_ids: Set[str] = set()
    start = 0

    while True:
        end = start + page_size - 1

        response = (
            supabase
            .table(table_name)
            .select("user_id")
            .not_.is_("user_id", "null")
            .range(start, end)
            .execute()
        )

        rows = response.data or []

        if not rows:
            break

        for row in rows:
            user_id = row.get("user_id")

            if user_id:
                user_ids.add(str(user_id))

        if len(rows) < page_size:
            break

        start += page_size

    return sorted(user_ids)


def get_user_book_count(user_id: str) -> int:
    user_books = fetch_user_books(user_id)
    return len(user_books)


def should_generate_for_user(user_id: str, min_books: int) -> bool:
    book_count = get_user_book_count(user_id)

    if book_count < min_books:
        print(
            f"Skipping user {user_id}: only {book_count} book(s), "
            f"minimum required is {min_books}."
        )
        return False

    return True


def generate_for_single_user(
    user_id: str,
    recommendation_limit: int,
    min_books: int,
    dry_run: bool = False,
) -> bool:
    print("")
    print("=" * 80)
    print(f"User: {user_id}")
    print("=" * 80)

    if not should_generate_for_user(user_id=user_id, min_books=min_books):
        return False

    if dry_run:
        book_count = get_user_book_count(user_id)
        print(
            f"[DRY RUN] Would generate {recommendation_limit} recommendations "
            f"for user {user_id} with {book_count} book(s)."
        )
        return True

    try:
        recommendations = generate_and_save_recommendations_for_user(
            user_id=user_id,
            limit=recommendation_limit,
            recommendation_type="personalized",
        )

        print(
            f"Success: generated and saved {len(recommendations)} "
            f"recommendation(s) for user {user_id}."
        )

        return True

    except Exception as error:
        print(f"Failed for user {user_id}: {error}")
        return False


def generate_for_all_users(
    recommendation_limit: int = 10,
    min_books: int = 1,
    max_users: Optional[int] = None,
    dry_run: bool = False,
    sleep_seconds: float = 0.0,
) -> None:
    print("Book Bulk Recommendation Generator")
    print("-----------------------------------------")
    print(f"Recommendation limit per user: {recommendation_limit}")
    print(f"Minimum books required: {min_books}")
    print(f"Dry run: {dry_run}")
    print("")

    print("Fetching users from books table...")
    user_ids = fetch_all_user_ids_from_books()

    if not user_ids:
        print("No users found in the books table.")
        return

    if max_users is not None:
        user_ids = user_ids[:max_users]

    print(f"Found {len(user_ids)} user(s) to process.")

    processed_count = 0
    success_count = 0
    skipped_or_failed_count = 0

    for user_id in user_ids:
        processed_count += 1

        success = generate_for_single_user(
            user_id=user_id,
            recommendation_limit=recommendation_limit,
            min_books=min_books,
            dry_run=dry_run,
        )

        if success:
            success_count += 1
        else:
            skipped_or_failed_count += 1

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    print("")
    print("=" * 80)
    print("Bulk generation complete.")
    print("=" * 80)
    print(f"Users processed: {processed_count}")
    print(f"Successful / dry-run eligible: {success_count}")
    print(f"Skipped or failed: {skipped_or_failed_count}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate personalized Book recommendations for all users."
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of recommendations to save per user. Default: 10.",
    )

    parser.add_argument(
        "--min-books",
        type=int,
        default=1,
        help="Minimum number of books a user must have before generating recommendations. Default: 1.",
    )

    parser.add_argument(
        "--max-users",
        type=int,
        default=None,
        help="Optional maximum number of users to process. Useful for testing.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview which users would be processed without saving recommendations.",
    )

    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="Seconds to wait between users. Useful if you want to slow down database requests.",
    )

    return parser.parse_args()


def main() -> None:
    load_dotenv()

    args = parse_args()

    if args.limit < 1:
        raise ValueError("--limit must be at least 1.")

    if args.min_books < 1:
        raise ValueError("--min-books must be at least 1.")

    generate_for_all_users(
        recommendation_limit=args.limit,
        min_books=args.min_books,
        max_users=args.max_users,
        dry_run=args.dry_run,
        sleep_seconds=args.sleep,
    )


if __name__ == "__main__":
    main()