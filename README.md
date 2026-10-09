👨‍💻 Author - 
Abhinandan Mahanta ,
GitHub: ABHINANDAN-M ,
LinkedIn: https://www.linkedin.com/in/abhinandan-mahanta-0065a028b/?isSelfProfile=true

# Bulk Certificate Generator

## About the Project

The Bulk Certificate Generator is a Python-based backend project that makes it easier to create certificates for multiple participants at once. It is useful for events, workshops, courses, and training programs where generating certificates manually can take a lot of time.

The API allows users to submit recipient details, generate personalized PDF certificates, check the generation status, and download the certificates when they are ready.

## Features

* Generate certificates for multiple recipients in one request.
* Validate recipient details before processing.
* Create personalized PDF certificates using a predefined template.
* Track job status and generation progress.
* Handle individual certificate failures without stopping the entire job.
* Download generated certificates through API endpoints.
* Verify certificates using a unique certificate ID.
* Test the main features using automated tests.
* Run the application using Docker.

## Technologies Used

* **Language:** Python
* **Backend Framework:** FastAPI
* **Database:** MongoDB
* **API Documentation:** Swagger UI
* **Testing:** Pytest
* **Containerization:** Docker
* **Output Format:** PDF

## Getting Started

### 1. Clone the Repository

```bash
git clone <your-github-repository-url>
cd bulk-certificate-generator
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create your `.env` file from the example:

```bash
copy .env.example .env
```

For macOS or Linux, use `cp .env.example .env`.

Configure your MongoDB connection string and other required settings in the `.env` file.

### 5. Start MongoDB

You can use a local MongoDB instance or MongoDB Atlas. For Docker, run:

```bash
docker run -d -p 27017:27017 --name mongo mongo:7
```

### 6. Run the Application

```bash
uvicorn app.main:app --reload
```

Open **http://localhost:8000/docs** to explore and test the API.

## Running Tests

Run the following command from the project directory:

```bash
pytest -v
```

## Main API Endpoints

| Method | Endpoint                                         | Purpose                             |
| ------ | ------------------------------------------------ | ----------------------------------- |
| POST   | `/api/v1/jobs`                                   | Create a certificate generation job |
| GET    | `/api/v1/jobs/{job_id}`                          | Check job status and progress       |
| GET    | `/api/v1/jobs/{job_id}/certificates`             | List generated certificates         |
| GET    | `/api/v1/certificates/{certificate_id}/download` | Download a certificate              |
| GET    | `/verify/{certificate_id}`                       | Verify a certificate                |

## Project Goal

The aim of this project is to reduce manual work, make certificate generation faster, and provide a simple way to manage and verify certificates through APIs.
