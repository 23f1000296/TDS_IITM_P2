# TDS_IITM_P2
---
title: LLM Quiz Solver
emoji: 🤖
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
license: mit
---

# 🤖 LLM Analysis Quiz Solver

Automated quiz-solving system for LLM Analysis course project at IIT Madras.

## 🚀 Features

- ✅ Automated quiz solving with OpenAI GPT-4o
- ✅ Handles PDFs, CSVs, Excel, Images, JSON and more
- ✅ JavaScript-rendered page support via Playwright
- ✅ Quiz chaining (solves multiple quizzes automatically)
- ✅ 3-minute timeout management
- ✅ Secret verification and error handling

## 🔧 API Endpoint

### POST `/project2`

Submit a quiz task for processing.

**Request Body:**
```json
{
  "email": "your-email@example.com",
  "secret": "your-secret-key",
  "url": "https://quiz-url.com/quiz-123"
}
```

**Responses:**
- `200 OK` - Quiz accepted and processing started
- `403 Forbidden` - Invalid secret key
- `400 Bad Request` - Invalid request format/JSON

**Example:**
```bash
curl -X POST https://YOUR-USERNAME-llm-quiz-solver.hf.space/project2 \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@example.com",
    "secret": "your-secret",
    "url": "https://example.com/quiz-123"
  }'
```

## 🏥 Health Check

### GET `/health`

Check if the service is running.

**Response:**
```json
{
  "status": "ok",
  "solver_ready": true
}
```

## 🔐 Environment Variables

This Space requires the following secrets (configured in Settings):

- `STUDENT_EMAIL` - Your student email address
- `SECRET_KEY` - Your secret key from Google Form submission
- `OPENAI_API_KEY` - Your OpenAI API key

**⚠️ Important:** These must be set in Space Settings → Variables and Secrets, **NOT** in code!

## 📚 Tech Stack

- **FastAPI** - Web framework
- **OpenAI GPT-4o** - LLM for reasoning and analysis
- **Playwright** - Headless browser for JavaScript rendering
- **Pandas & NumPy** - Data processing
- **pdfplumber** - PDF text and table extraction
- **aiohttp** - Async HTTP client

## 🎯 How It Works

1. Receives quiz URL via POST request
2. Verifies secret key
3. Fetches and renders quiz page (handles JavaScript)
4. Extracts question (decodes base64 if needed)
5. Uses Gemini AI to understand the task
6. Downloads required files (PDFs, CSVs, images)
7. Processes and analyzes data
8. Generates answer
9. Submits answer to specified endpoint
10. Chains to next quiz if provided

## 📝 Supported Question Types

- ✅ **File Download & Analysis** - Download PDFs/CSVs and compute statistics
- ✅ **Web Scraping** - Extract data from JavaScript-rendered pages
- ✅ **Data Processing** - Filter, aggregate, transform datasets
- ✅ **Image Analysis** - OCR and vision-based analysis with GPT-4o Vision
- ✅ **API Calls** - Fetch and process JSON data
- ✅ **Visualizations** - Generate charts (returned as base64)

## 🎓 Academic Project

This is a legitimate course assignment for the **LLM Analysis course at IIT Madras**, where students are required to build automated quiz-solving systems as part of their coursework.

## 📄 License

MIT License

## 👨‍💻 Author

IIT Madras Student - LLM Analysis Course Project

---

**Note:** This Space is deployed for academic evaluation purposes. The quiz-solving endpoint will be active during the designated evaluation period (Sat 29 Nov 2025, 3:00 PM - 4:00 PM IST).�
