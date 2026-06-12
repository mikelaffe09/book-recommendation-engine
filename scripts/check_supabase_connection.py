import os
from dotenv import load_dotenv
from supabase import create_client, Client


def get_required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value


def get_supabase_client() -> Client:
    load_dotenv()

    supabase_url = get_required_env("SUPABASE_URL")
    supabase_key = get_required_env("SUPABASE_SERVICE_ROLE_KEY")

    return create_client(supabase_url, supabase_key)


def fetch_sample_books(limit: int = 10):
    supabase = get_supabase_client()

    table_name = os.getenv("SUPABASE_BOOK_CATALOGUE_TABLE", "book_catalogue")

    response = (
        supabase
        .table(table_name)
        .select(
            "id, title, author, genre, description, total_pages, "
            "published_year, publisher, series, series_order, tags, cover_url, isbn"
        )
        .limit(limit)
        .execute()
    )

    return response.data or []


def main():
    print("Testing Supabase connection...")
    print("Fetching sample books from book_catalogue...\n")

    books = fetch_sample_books(limit=10)

    if not books:
        print("Connected, but no books were returned.")
        print("This usually means one of these:")
        print("- The table is empty")
        print("- Your Supabase service role key does not have permission")
        print("- RLS is blocking the request")
        return

    print(f"Success. Found {len(books)} sample books:\n")

    for index, book in enumerate(books, start=1):
        title = book.get("title") or "Untitled"
        author = book.get("author") or "Unknown author"
        genre = book.get("genre") or "No genre"
        pages = book.get("total_pages") or "Unknown pages"

        print(f"{index}. {title}")
        print(f"   Author: {author}")
        print(f"   Genre: {genre}")
        print(f"   Pages: {pages}")
        print()


if __name__ == "__main__":
    main()
