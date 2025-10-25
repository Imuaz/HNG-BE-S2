# Country Currency & Exchange API

A RESTful API built with Django REST Framework that fetches country data, currency exchange rates, and provides CRUD operations.

## Features

- Fetch and cache country data from external APIs
- Calculate estimated GDP for each country
- Filter and sort countries by region, currency, GDP, population
- Generate summary images with statistics
- Full CRUD operations

## Setup Instructions

### Prerequisites

- Python 3.8+
- MySQL 5.7+
- pip

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd country_currency_api
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create MySQL database:
```sql
CREATE DATABASE country_currency_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

5. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

6. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

7. Start the development server:
```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000`

## API Endpoints

### 1. Refresh Countries Data
```http
POST /countries/refresh
```

Fetches data from external APIs and updates the database.

**Response:**
```json
{
  "message": "Countries refreshed successfully",
  "total_countries": 250,
  "created": 10,
  "updated": 240,
  "last_refreshed_at": "2025-10-25T10:00:00Z"
}
```

### 2. List All Countries
```http
GET /countries
GET /countries?region=Africa
GET /countries?currency=NGN
GET /countries?sort=gdp_desc
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "Nigeria",
    "capital": "Abuja",
    "region": "Africa",
    "population": 206139589,
    "currency_code": "NGN",
    "exchange_rate": "1600.230000",
    "estimated_gdp": "25767448125.20",
    "flag_url": "https://flagcdn.com/ng.svg",
    "last_refreshed_at": "2025-10-25T10:00:00Z"
  }
]
```

### 3. Get Single Country
```http
GET /countries/Nigeria
```

### 4. Delete Country
```http
DELETE /countries

```

**Response:**
```json
{
  "message": "Country \"Nigeria\" deleted successfully"
}
```

### 5. Get Status
```http
GET /status
```

**Response:**
```json
{
  "total_countries": 250,
  "last_refreshed_at": "2025-10-25T10:00:00Z"
}
```

### 6. Get Summary Image
```http
GET /countries/image
```

Returns a PNG image with statistics.

## Query Parameters

### Filtering
- `region` - Filter by region (e.g., `?region=Africa`)
- `currency` - Filter by currency code (e.g., `?currency=NGN`)

### Sorting
- `sort=gdp_desc` - Sort by GDP descending
- `sort=gdp_asc` - Sort by GDP ascending
- `sort=population_desc` - Sort by population descending
- `sort=population_asc` - Sort by population ascending
- `sort=name_desc` - Sort by name Z-A
- `sort=name_asc` - Sort by name A-Z

## Error Responses

### 400 Bad Request
```json
{
  "error": "Validation failed",
  "details": {
    "currency_code": "is required"
  }
}
```

### 404 Not Found
```json
{
  "error": "Country not found"
}
```

### 503 Service Unavailable
```json
{
  "error": "External data source unavailable",
  "details": "Could not fetch data from REST Countries API"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error"
}
```

## Testing

Test the API using curl or any HTTP client:
```bash
# Refresh data
curl -X POST http://localhost:8000/countries/refresh

# Get all countries
curl http://localhost:8000/countries

# Filter by region
curl http://localhost:8000/countries?region=Africa

# Get single country
curl http://localhost:8000/countries/Nigeria

# Get status
curl http://localhost:8000/status

# Get image
curl http://localhost:8000/countries/image --output summary.png
```

## Project Structure
```
country_currency_api/
├── manage.py
├── .env
├── requirements.txt
├── README.md
├── cache/                  # Generated images
├── config/                 # Project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── countries/              # Main app
    ├── models.py          # Database models
    ├── serializers.py     # Data validation
    ├── views.py           # API endpoints
    ├── urls.py            # Route definitions
    ├── services.py        # Business logic
    └── utils.py           # Helper functions
```

## License

MIT