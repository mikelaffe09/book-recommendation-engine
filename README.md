# Personalized Book Recommendation Engine

A Python-based recommendation engine that generates personalized book suggestions based on a user's reading history, ratings, genres, authors, and saved books.

This project was built as a standalone backend service for generating book recommendations. It uses content-based filtering with TF-IDF vectorization and cosine similarity to compare books and recommend relevant titles to users.

## Overview

The goal of this project is to provide a simple, clean, and extendable recommendation engine that can be used by reading apps, book-tracking platforms, digital libraries, or personal recommendation tools.

The engine analyzes a user's book collection and compares it against a catalogue of available books. It then ranks recommendations using text similarity, genre matching, user rating signals, and duplicate filtering.

## Features

* Personalized book recommendations
* Content-based recommendation logic
* TF-IDF vectorization
* Cosine similarity scoring
* Genre-based ranking adjustments
* Positive and negative user preference signals
* Duplicate filtering using ISBN, title, and author matching
* Supabase integration for storing books and recommendations
* FastAPI backend endpoint
* Internal API secret protection
* Bulk recommendation script for multiple users
* Manual scripts for checking database connection and recommendation output

## Tech Stack

* Python
* FastAPI
* Supabase
* pandas
* NumPy
* scikit-learn
* python-dotenv
* Uvicorn

## Project Structure

```txt
book-recommendation-engine/
├─ app/
│  ├─ __init__.py
│  ├─ main.py
│  ├─ recommender.py
│  └─ recommendation_service.py
├─ scripts/
│  ├─ __init__.py
│  ├─ check_supabase_connection.py
│  ├─ check_user_books.py
│  ├─ demo_similar_books.py
│  ├─ generate_for_all_users.py
│  └─ verify_user_recommendations.py
├─ .env.example
├─ .gitignore
├─ Procfile
├─ README.md
├─ LICENSE
└─ requirements.txt
```

## How It Works

The recommendation engine follows these steps:

1. Fetches the user's saved/read books from the database.
2. Fetches the full book catalogue.
3. Builds a text profile for each book using fields such as title, author, genre, and description.
4. Uses TF-IDF to convert book text into numerical vectors.
5. Uses cosine similarity to compare books.
6. Gives higher weight to books similar to positively rated books.
7. Reduces recommendation score for books similar to disliked or low-rated books.
8. Applies genre-based boosts.
9. Removes duplicates and books the user already has.
10. Saves the final recommendations to the database.

## Recommendation Logic

The engine uses content-based filtering.

Instead of recommending books based on other users, it recommends books based on the current user's own reading profile.

The main scoring signals include:

* Book title similarity
* Author similarity
* Genre similarity
* Description similarity
* User rating history
* Books marked as completed or saved
* Books already owned by the user
* Duplicate ISBN/title/author checks

This makes the engine useful even without a large user base.

## Requirements

Install Python 3.10 or later.

Recommended:

```bash
python --version
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Activate it on Git Bash:

```bash
source .venv/Scripts/activate
```

Activate it on macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Environment Variables

Create a local `.env` file based on `.env.example`.

Do not commit your real `.env` file.

```env
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key

SUPABASE_BOOK_CATALOGUE_TABLE=book_catalogue
SUPABASE_USER_BOOKS_TABLE=books
SUPABASE_RECOMMENDATIONS_TABLE=book_recommendations

RECOMMENDER_INTERNAL_SECRET=replace-with-a-long-random-secret

API_TITLE=Personalized Book Recommendation API
API_VERSION=1.0.0
API_SERVICE_NAME=book-recommendation-engine
```

## Security Notes

This project uses environment variables for private credentials.

Never commit:

```txt
.env
.venv/
__pycache__/
*.pyc
*.log
```

The Supabase service role key should only be used in a trusted backend environment.

Do not expose the service role key in:

* frontend apps
* mobile apps
* browser code
* public repositories
* client-side JavaScript

If a real key is accidentally committed, rotate it immediately in Supabase.

## Running the API

Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

The API should run locally at:

```txt
http://127.0.0.1:8000
```

## API Endpoints

### Health Check

```http
GET /health
```

Example response:

```json
{
  "status": "ok",
  "service": "book-recommendation-engine"
}
```

### Generate Recommendations

```http
POST /recommendations/generate
```

Required header:

```http
x-recommender-secret: your-internal-secret
```

Example request body:

```json
{
  "user_id": "example-user-id",
  "limit": 10
}
```

Example response:

```json
{
  "success": true,
  "user_id": "example-user-id",
  "recommendations_saved": 10
}
```

## Running Scripts

Run scripts from the project root using Python module syntax.

Check Supabase connection:

```bash
python -m scripts.check_supabase_connection
```

Check books for a specific user:

```bash
python -m scripts.check_user_books
```

Run a similar-books demo:

```bash
python -m scripts.demo_similar_books
```

Generate recommendations for all users:

```bash
python -m scripts.generate_for_all_users
```

Verify recommendations for one user:

```bash
python -m scripts.verify_user_recommendations
```

## Database Tables

This project expects three main Supabase tables.

### Book Catalogue Table

Default table name:

```txt
book_catalogue
```

Expected fields may include:

```txt
id
title
author
description
genre
isbn
cover_url
created_at
```

### User Books Table

Default table name:

```txt
books
```

Expected fields may include:

```txt
id
user_id
title
author
description
genre
isbn
rating
status
created_at
```

### Recommendations Table

Default table name:

```txt
book_recommendations
```

Expected fields may include:

```txt
id
user_id
book_id
title
author
description
genre
isbn
score
reason
created_at
```

The table names can be changed using environment variables.

## Example Use Cases

This engine can be used for:

* reading tracker apps
* book recommendation apps
* personal library tools
* digital book catalogues
* educational reading platforms
* backend portfolio projects
* recommendation system experiments

## Deployment

This project can be deployed to platforms that support Python web services, such as:

* Render
* Railway
* Fly.io
* Heroku-style platforms
* VPS servers

If using the included `Procfile`, the process command should be:

```txt
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Development Checklist

Before pushing changes publicly:

```bash
python -m compileall app scripts
```

Check that no secrets are included:

```powershell
Get-ChildItem -Recurse -File | Select-String -Pattern "service_role|eyJ|SUPABASE_SERVICE_ROLE_KEY|RECOMMENDER_INTERNAL_SECRET" -List
```

Make sure these files are not committed:

```txt
.env
.venv/
__pycache__/
*.pyc
*.log
```

## Limitations

This project uses content-based filtering only.

It does not currently include:

* collaborative filtering
* user-to-user similarity
* real-time model training
* advanced NLP embeddings
* external book API enrichment
* admin dashboard
* automated test suite

These would be good future improvements.

## Future Improvements

Possible upgrades:

* Add sample data mode for running without Supabase
* Add unit tests with pytest
* Add Docker support
* Add API documentation examples
* Add OpenAPI request/response schemas
* Add recommendation explanation messages
* Add collaborative filtering
* Add vector embeddings for better semantic recommendations
* Add CI checks using GitHub Actions
* Add rate limiting
* Add admin-only bulk generation endpoint

## License

This project is open-source and available under the MIT License.

## Author

Built by Mike Laffe as a standalone Python backend project for generating personalized book recommendations.
