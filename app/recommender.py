import os
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from supabase import Client, create_client


Book = Dict[str, Any]


# ------------------------------------------------------------
# ENV + SUPABASE
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# BASIC CLEANING HELPERS
# ------------------------------------------------------------

def normalize_value(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        return " ".join(normalize_value(item) for item in value)

    if isinstance(value, dict):
        return " ".join(normalize_value(item) for item in value.values())

    return str(value).strip()


def normalize_key(value: Any) -> str:
    text = normalize_value(value).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def split_tags_or_genres(value: Any) -> List[str]:
    text = normalize_value(value).lower()

    if not text:
        return []

    parts = re.split(r"[;,|/]+", text)

    return [
        part.strip()
        for part in parts
        if part.strip()
    ]


def build_book_text(book: Book) -> str:
    fields = [
        book.get("title"),
        book.get("author"),
        book.get("genre"),
        book.get("description"),
        book.get("publisher"),
        book.get("series"),
        book.get("tags"),
        book.get("format"),
    ]

    return " ".join(normalize_value(field) for field in fields).lower()


def build_existing_book_keys(user_books: List[Book]) -> Tuple[set, set]:
    existing_isbns = set()
    existing_title_author_keys = set()

    for book in user_books:
        isbn = normalize_key(book.get("isbn"))

        if isbn:
            existing_isbns.add(isbn)

        title = normalize_key(book.get("title"))
        author = normalize_key(book.get("author"))

        if title and author:
            existing_title_author_keys.add(f"{title}::{author}")

    return existing_isbns, existing_title_author_keys


def is_book_already_in_user_library(
    catalogue_book: Book,
    existing_isbns: set,
    existing_title_author_keys: set
) -> bool:
    isbn = normalize_key(catalogue_book.get("isbn"))

    if isbn and isbn in existing_isbns:
        return True

    title = normalize_key(catalogue_book.get("title"))
    author = normalize_key(catalogue_book.get("author"))

    if title and author and f"{title}::{author}" in existing_title_author_keys:
        return True

    return False


# ------------------------------------------------------------
# SUPABASE FETCHING
# ------------------------------------------------------------

def fetch_all_catalogue_books(page_size: int = 1000) -> List[Book]:
    supabase = get_supabase_client()
    table_name = os.getenv("SUPABASE_BOOK_CATALOGUE_TABLE", "book_catalogue")

    all_books: List[Book] = []
    start = 0

    while True:
        end = start + page_size - 1

        response = (
            supabase
            .table(table_name)
            .select(
                "id, title, author, cover_url, isbn, genre, description, "
                "total_pages, published_year, publisher, series, "
                "series_order, tags, created_at, updated_at"
            )
            .range(start, end)
            .execute()
        )

        batch = response.data or []

        if not batch:
            break

        all_books.extend(batch)

        if len(batch) < page_size:
            break

        start += page_size

    return all_books


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
        .execute()
    )

    return response.data or []


# ------------------------------------------------------------
# DATAFRAME BUILDING
# ------------------------------------------------------------

def build_catalogue_dataframe(books: List[Book]) -> pd.DataFrame:
    if not books:
        raise ValueError("No catalogue books found.")

    df = pd.DataFrame(books)

    required_columns = [
        "id",
        "title",
        "author",
        "cover_url",
        "isbn",
        "genre",
        "description",
        "total_pages",
        "published_year",
        "publisher",
        "series",
        "series_order",
        "tags",
    ]

    for column in required_columns:
        if column not in df.columns:
            df[column] = ""

    df["combined_features"] = df.apply(
        lambda row: build_book_text(row.to_dict()),
        axis=1
    )

    return df


def build_user_books_dataframe(user_books: List[Book]) -> pd.DataFrame:
    if not user_books:
        raise ValueError("No user books found.")

    df = pd.DataFrame(user_books)

    required_columns = [
        "id",
        "title",
        "author",
        "genre",
        "isbn",
        "tags",
        "status",
        "format",
        "progress",
        "rating",
        "review",
        "total_pages",
    ]

    for column in required_columns:
        if column not in df.columns:
            df[column] = ""

    df["combined_features"] = df.apply(
        lambda row: build_book_text(row.to_dict()),
        axis=1
    )

    return df


# ------------------------------------------------------------
# SIGNAL WEIGHTING
# ------------------------------------------------------------

def get_user_book_signal_weight(book: Book) -> float:
    """
    Positive weight means: user probably likes this kind of book.
    Negative weight means: user probably does not like this kind of book.

    This is not perfect, but it is a strong MVP.
    """
    status = normalize_value(book.get("status")).lower()
    rating = safe_float(book.get("rating"), default=0.0)
    progress = safe_float(book.get("progress"), default=0.0)

    negative_statuses = {
        "dnf",
        "abandoned",
        "dropped",
        "did not finish",
        "not finished",
    }

    strong_positive_statuses = {
        "completed",
        "complete",
        "finished",
        "read",
    }

    medium_positive_statuses = {
        "reading",
        "currently reading",
        "ongoing",
        "in progress",
    }

    weak_positive_statuses = {
        "saved",
        "wishlist",
        "want to read",
        "tbr",
        "to be read",
    }

    if status in negative_statuses:
        return -1.0

    if rating > 0:
        if rating >= 4.5:
            return 1.25
        if rating >= 4:
            return 1.0
        if rating >= 3:
            return 0.55
        if rating <= 2:
            return -0.85

    if status in strong_positive_statuses:
        return 1.0

    if status in medium_positive_statuses:
        return 0.7

    if status in weak_positive_statuses:
        return 0.3

    if progress >= 90:
        return 0.8

    if progress >= 40:
        return 0.45

    return 0.15


def get_top_user_genres(user_books: List[Book], limit: int = 5) -> List[str]:
    genre_scores: Dict[str, float] = {}

    for book in user_books:
        weight = get_user_book_signal_weight(book)

        if weight <= 0:
            continue

        genres = split_tags_or_genres(book.get("genre"))

        for genre in genres:
            genre_scores[genre] = genre_scores.get(genre, 0.0) + weight

    sorted_genres = sorted(
        genre_scores.items(),
        key=lambda item: item[1],
        reverse=True
    )

    return [genre for genre, _ in sorted_genres[:limit]]


def genre_match_score(catalogue_book: Book, favorite_genres: List[str]) -> float:
    if not favorite_genres:
        return 0.0

    book_genres = set(split_tags_or_genres(catalogue_book.get("genre")))
    favorite_set = set(favorite_genres)

    if not book_genres:
        return 0.0

    overlap = book_genres.intersection(favorite_set)

    if not overlap:
        return 0.0

    return min(len(overlap) / max(len(favorite_set), 1), 1.0)


# ------------------------------------------------------------
# SIMILAR BOOK RECOMMENDER
# ------------------------------------------------------------

def get_book_by_id(df: pd.DataFrame, book_id: str) -> Optional[pd.Series]:
    matches = df[df["id"].astype(str) == str(book_id)]

    if matches.empty:
        return None

    return matches.iloc[0]


def recommend_similar_books(book_id: str, limit: int = 10) -> List[Book]:
    catalogue_books = fetch_all_catalogue_books()
    df = build_catalogue_dataframe(catalogue_books)

    selected_book = get_book_by_id(df, book_id)

    if selected_book is None:
        raise ValueError(f"No book found with id: {book_id}")

    vectorizer = TfidfVectorizer(
        stop_words="english",
        min_df=1,
        ngram_range=(1, 2)
    )

    tfidf_matrix = vectorizer.fit_transform(df["combined_features"])
    selected_index = selected_book.name

    similarity_scores = cosine_similarity(
        tfidf_matrix[selected_index],
        tfidf_matrix
    ).flatten()

    df["similarity_score"] = similarity_scores

    recommendations = (
        df[df["id"].astype(str) != str(book_id)]
        .sort_values(by="similarity_score", ascending=False)
        .head(limit)
    )

    results: List[Book] = []

    for _, row in recommendations.iterrows():
        results.append({
            "id": row.get("id"),
            "title": row.get("title"),
            "author": row.get("author"),
            "genre": row.get("genre"),
            "description": row.get("description"),
            "total_pages": row.get("total_pages"),
            "published_year": row.get("published_year"),
            "publisher": row.get("publisher"),
            "series": row.get("series"),
            "cover_url": row.get("cover_url"),
            "isbn": row.get("isbn"),
            "score": round(float(row.get("similarity_score", 0)), 4),
            "similarity_score": round(float(row.get("similarity_score", 0)), 4),
            "reason": build_similar_book_reason(selected_book, row),
            "recommendation_type": "similar_book",
        })

    return results


def build_similar_book_reason(
    selected_book: pd.Series,
    recommended_book: pd.Series
) -> str:
    selected_title = normalize_value(selected_book.get("title")) or "the selected book"
    selected_genre = normalize_value(selected_book.get("genre"))
    recommended_genre = normalize_value(recommended_book.get("genre"))

    if selected_genre and recommended_genre and selected_genre.lower() == recommended_genre.lower():
        return f"Recommended because it shares the same genre as {selected_title}."

    return f"Recommended because its metadata and themes are similar to {selected_title}."


# ------------------------------------------------------------
# PERSONALIZED USER RECOMMENDER
# ------------------------------------------------------------

def recommend_books_for_user(user_id: str, limit: int = 10) -> List[Book]:
    """
    Builds a taste profile from user's saved/read/rated books,
    compares it against book_catalogue, and returns recommended books.
    """
    catalogue_books = fetch_all_catalogue_books()
    user_books = fetch_user_books(user_id)

    if not user_books:
        raise ValueError("This user has no books. Cannot build personalized recommendations.")

    catalogue_df = build_catalogue_dataframe(catalogue_books)
    user_df = build_user_books_dataframe(user_books)

    existing_isbns, existing_title_author_keys = build_existing_book_keys(user_books)
    favorite_genres = get_top_user_genres(user_books)

    catalogue_df["already_in_library"] = catalogue_df.apply(
        lambda row: is_book_already_in_user_library(
            row.to_dict(),
            existing_isbns,
            existing_title_author_keys
        ),
        axis=1
    )

    available_catalogue_df = catalogue_df[catalogue_df["already_in_library"] == False].copy()

    if available_catalogue_df.empty:
        return []

    positive_user_rows = []
    positive_weights = []

    negative_user_rows = []
    negative_weights = []

    for _, row in user_df.iterrows():
        book = row.to_dict()
        weight = get_user_book_signal_weight(book)

        if weight > 0:
            positive_user_rows.append(row)
            positive_weights.append(weight)

        elif weight < 0:
            negative_user_rows.append(row)
            negative_weights.append(abs(weight))

    if not positive_user_rows:
        raise ValueError(
            "No positive user signals found. The user may only have DNF/low-rated books."
        )

    positive_user_texts = [
        row["combined_features"]
        for row in positive_user_rows
    ]

    negative_user_texts = [
        row["combined_features"]
        for row in negative_user_rows
    ]

    catalogue_texts = available_catalogue_df["combined_features"].tolist()

    all_texts = catalogue_texts + positive_user_texts + negative_user_texts

    vectorizer = TfidfVectorizer(
        stop_words="english",
        min_df=1,
        ngram_range=(1, 2)
    )

    tfidf_matrix = vectorizer.fit_transform(all_texts)

    catalogue_matrix = tfidf_matrix[:len(catalogue_texts)]

    positive_start = len(catalogue_texts)
    positive_end = positive_start + len(positive_user_texts)
    positive_matrix = tfidf_matrix[positive_start:positive_end]

    positive_profile = np.average(
        positive_matrix.toarray(),
        axis=0,
        weights=np.array(positive_weights)
    ).reshape(1, -1)

    positive_similarity = cosine_similarity(
        positive_profile,
        catalogue_matrix
    ).flatten()

    negative_similarity = np.zeros(len(catalogue_texts))

    if negative_user_texts:
        negative_start = positive_end
        negative_end = negative_start + len(negative_user_texts)
        negative_matrix = tfidf_matrix[negative_start:negative_end]

        negative_profile = np.average(
            negative_matrix.toarray(),
            axis=0,
            weights=np.array(negative_weights)
        ).reshape(1, -1)

        negative_similarity = cosine_similarity(
            negative_profile,
            catalogue_matrix
        ).flatten()

    available_catalogue_df["positive_similarity"] = positive_similarity
    available_catalogue_df["negative_similarity"] = negative_similarity

    available_catalogue_df["genre_bonus"] = available_catalogue_df.apply(
        lambda row: genre_match_score(row.to_dict(), favorite_genres),
        axis=1
    )

    available_catalogue_df["final_score"] = (
        available_catalogue_df["positive_similarity"] * 0.80
        + available_catalogue_df["genre_bonus"] * 0.15
        - available_catalogue_df["negative_similarity"] * 0.25
    )

    available_catalogue_df["final_score"] = available_catalogue_df["final_score"].clip(lower=0)

    recommendations = (
        available_catalogue_df
        .sort_values(by="final_score", ascending=False)
        .head(limit)
    )

    source_titles = get_source_titles_for_reason(user_books)

    results: List[Book] = []

    for _, row in recommendations.iterrows():
        results.append({
            "id": row.get("id"),
            "title": row.get("title"),
            "author": row.get("author"),
            "genre": row.get("genre"),
            "description": row.get("description"),
            "total_pages": row.get("total_pages"),
            "published_year": row.get("published_year"),
            "publisher": row.get("publisher"),
            "series": row.get("series"),
            "cover_url": row.get("cover_url"),
            "isbn": row.get("isbn"),
            "score": round(float(row.get("final_score", 0)), 4),
            "positive_similarity": round(float(row.get("positive_similarity", 0)), 4),
            "negative_similarity": round(float(row.get("negative_similarity", 0)), 4),
            "genre_bonus": round(float(row.get("genre_bonus", 0)), 4),
            "reason": build_personalized_reason(
                recommended_book=row.to_dict(),
                favorite_genres=favorite_genres,
                source_titles=source_titles
            ),
            "recommendation_type": "personalized",
        })

    return results


def get_source_titles_for_reason(user_books: List[Book], limit: int = 3) -> List[str]:
    positive_books = []

    for book in user_books:
        weight = get_user_book_signal_weight(book)

        if weight > 0:
            positive_books.append((book, weight))

    positive_books.sort(key=lambda item: item[1], reverse=True)

    titles = []

    for book, _ in positive_books[:limit]:
        title = normalize_value(book.get("title"))

        if title:
            titles.append(title)

    return titles


def build_personalized_reason(
    recommended_book: Book,
    favorite_genres: List[str],
    source_titles: List[str]
) -> str:
    recommended_genres = split_tags_or_genres(recommended_book.get("genre"))

    matched_genres = [
        genre
        for genre in recommended_genres
        if genre in favorite_genres
    ]

    if matched_genres and source_titles:
        return (
            f"Recommended because it matches your interest in "
            f"{', '.join(matched_genres[:2])} and is similar to books like "
            f"{', '.join(source_titles[:2])}."
        )

    if matched_genres:
        return (
            f"Recommended because it matches your interest in "
            f"{', '.join(matched_genres[:2])}."
        )

    if source_titles:
        return (
            f"Recommended because its themes are similar to books in your library, "
            f"including {', '.join(source_titles[:2])}."
        )

    return "Recommended because it matches patterns from your reading history."


# ------------------------------------------------------------
# QUICK MANUAL TEST
# ------------------------------------------------------------

if __name__ == "__main__":
    print(" Book Recommender")
    print("-----------------------")
    print("1. Similar books from one book ID")
    print("2. Personalized recommendations from user ID")

    choice = input("\nChoose 1 or 2: ").strip()

    if choice == "1":
        book_id = input("Paste book_catalogue ID: ").strip()
        results = recommend_similar_books(book_id=book_id, limit=10)

    elif choice == "2":
        user_id = input("Paste Supabase user_id: ").strip()
        results = recommend_books_for_user(user_id=user_id, limit=10)

    else:
        print("Invalid choice.")
        raise SystemExit

    print("\nRecommendations:\n")

    for index, book in enumerate(results, start=1):
        print(f"{index}. {book.get('title')} — {book.get('author')}")
        print(f"   Genre: {book.get('genre')}")
        print(f"   Score: {book.get('score')}")
        print(f"   Reason: {book.get('reason')}")
        print()