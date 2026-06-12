import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from supabase import Client, create_client


Book = Dict[str, Any]


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


def fetch_user_books(user_id: str) -> List[Book]:
    supabase = get_supabase_client()
    table_name = os.getenv("SUPABASE_USER_BOOKS_TABLE", "books")

    response = (
        supabase
        .table(table_name)
        .select(
            "id, user_id, title, author, cover_url, genre, series, series_order, "
            "isbn, tags, priority, status, format, progress, total_pages, "
            "rating, rating_plot, rating_characters, rating_writing, "
            "rating_pacing, rating_spice, review, content_warnings, "
            "date_added, date_started, date_completed, created_at, updated_at"
        )
        .eq("user_id", user_id)
        .order("date_added", desc=True)
        .execute()
    )

    return response.data or []


def summarize_user_books(books: List[Book]) -> None:
    if not books:
        print("No books found for this user.")
        print()
        print("Possible reasons:")
        print("- Wrong user_id")
        print("- User has no books")
        print("- RLS is blocking the script")
        print("- You are using anon key instead of service role key")
        return

    print(f"Found {len(books)} books for this user.\n")

    status_counts = {}

    for book in books:
        status = book.get("status") or "unknown"
        status_counts[status] = status_counts.get(status, 0) + 1

    print("Status summary:")
    for status, count in status_counts.items():
        print(f"- {status}: {count}")

    print("\nSample books:\n")

    for index, book in enumerate(books[:10], start=1):
        title = book.get("title") or "Untitled"
        author = book.get("author") or "Unknown author"
        genre = book.get("genre") or "No genre"
        status = book.get("status") or "No status"
        rating = book.get("rating")
        progress = book.get("progress")

        print(f"{index}. {title} — {author}")
        print(f"   Genre: {genre}")
        print(f"   Status: {status}")
        print(f"   Rating: {rating}")
        print(f"   Progress: {progress}%")
        print()


def main():
    print("Book User Library Test")
    print("-----------------------------")

    user_id = input("Paste a Supabase user_id: ").strip()

    if not user_id:
        print("No user_id provided. Exiting.")
        return

    try:
        books = fetch_user_books(user_id)
        summarize_user_books(books)

    except Exception as error:
        print("\nSomething went wrong:")
        print(error)


if __name__ == "__main__":
    main()