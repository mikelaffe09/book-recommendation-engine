import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from supabase import Client, create_client

from app.recommender import fetch_user_books, recommend_books_for_user
from app.recommendation_service import generate_and_save_recommendations_for_user


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


def print_user_books(user_books: List[Book]) -> None:
    print(f"\nFound {len(user_books)} books for this user.\n")

    if not user_books:
        print("No books found. The recommender cannot build a taste profile.")
        return

    for index, book in enumerate(user_books, start=1):
        print(f"{index}. {book.get('title')} — {book.get('author')}")
        print(f"   Status: {book.get('status')}")
        print(f"   Genre: {book.get('genre')}")
        print(f"   Rating: {book.get('rating')}")
        print(f"   Progress: {book.get('progress')}")
        print()


def fetch_saved_recommendations(user_id: str) -> List[Dict[str, Any]]:
    supabase = get_supabase_client()
    table_name = os.getenv("SUPABASE_RECOMMENDATIONS_TABLE", "book_recommendations")

    response = (
        supabase
        .table(table_name)
        .select("id, user_id, catalogue_book_id, title, author, genre, score, reason, recommendation_type")
        .eq("user_id", user_id)
        .eq("recommendation_type", "personalized")
        .order("score", desc=True)
        .execute()
    )

    return response.data or []


def main() -> None:
    print("Book Per-User Recommendation Verifier")
    print("--------------------------------------------")

    user_id = input("Paste the SECOND account Supabase user_id: ").strip()

    if not user_id:
        print("No user_id provided. Exiting.")
        return

    print("\nStep 1: Reading this user's books from Supabase...")
    user_books = fetch_user_books(user_id)
    print_user_books(user_books)

    if not user_books:
        print("Stop here. This user has no books in the books table.")
        return

    print("Step 2: Generating recommendations in memory...")
    recommendations = recommend_books_for_user(user_id=user_id, limit=10)

    print(f"\nGenerated {len(recommendations)} recommendations for this exact user.\n")

    for index, recommendation in enumerate(recommendations, start=1):
        print(f"{index}. {recommendation.get('title')} — {recommendation.get('author')}")
        print(f"   Score: {recommendation.get('score')}")
        print(f"   Reason: {recommendation.get('reason')}")
        print()

    print("Step 3: Saving recommendations into book_recommendations...")
    generate_and_save_recommendations_for_user(
        user_id=user_id,
        limit=10,
        recommendation_type="personalized",
    )

    print("\nStep 4: Reading saved recommendations back from Supabase...")
    saved_recommendations = fetch_saved_recommendations(user_id)

    print(f"\nSaved rows found for this user: {len(saved_recommendations)}\n")

    for index, recommendation in enumerate(saved_recommendations, start=1):
        print(f"{index}. {recommendation.get('title')} — {recommendation.get('author')}")
        print(f"   user_id: {recommendation.get('user_id')}")
        print(f"   Score: {recommendation.get('score')}")
        print()

    print("Verification complete.")
    print("Now open the app with this same account and refresh the Library tab.")


if __name__ == "__main__":
    main()