from app.recommender import recommend_similar_books


def main():
    print("Book Similar Book Recommender")
    print("------------------------------------")

    book_id = input("Paste a book_catalogue ID: ").strip()

    if not book_id:
        print("No book ID provided. Exiting.")
        return

    try:
        recommendations = recommend_similar_books(book_id=book_id, limit=10)

        if not recommendations:
            print("No similar books found.")
            return

        print("\nRecommended similar books:\n")

        for index, book in enumerate(recommendations, start=1):
            print(f"{index}. {book.get('title')} — {book.get('author')}")
            print(f"   Genre: {book.get('genre')}")
            print(f"   Pages: {book.get('total_pages')}")
            print(f"   Year: {book.get('published_year')}")
            print(f"   Score: {book.get('similarity_score')}")
            print(f"   Reason: {book.get('reason')}")
            print()

    except Exception as error:
        print("\nSomething went wrong:")
        print(error)


if __name__ == "__main__":
    main()