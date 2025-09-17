# Multi_DiscordBot

## Overview
This project is a LinkedIn Job Search Dashboard that allows users to scrape LinkedIn job postings, save them to a database, and track their application statuses. It includes a Flask backend and a React frontend.

---

## Prerequisites
To run this project, you need the following installed:
- Python 3.x
- Node.js
- Git
- Supabase account
  - Run this sql code in the sql editor if you're first getting started:
```bash
-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.Users (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  user_uuid uuid DEFAULT gen_random_uuid(),
  Experiences jsonb,
  Projects jsonb,
  Skills jsonb,
  CONSTRAINT Users_pkey PRIMARY KEY (id)
);
CREATE TABLE public.user_jobs (
  id integer NOT NULL DEFAULT nextval('user_jobs_id_seq'::regclass),
  user_id uuid,
  job_name character varying NOT NULL,
  company character varying NOT NULL,
  location character varying,
  location_type character varying,
  job_type character varying,
  posting_date character varying,
  application_link text NOT NULL UNIQUE,
  description text,
  source character varying DEFAULT 'linkedin'::character varying,
  scraped_at timestamp with time zone DEFAULT now(),
  created_at timestamp with time zone DEFAULT now(),
  application_status character varying DEFAULT 'not_applied'::character varying,
  status_updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT user_jobs_pkey PRIMARY KEY (id),
  CONSTRAINT user_jobs_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id)
);
```
    
- `.env` files for both the backend and frontend

---

## Directory Structure
- **`backend/`**: Contains the Flask backend and job scraping logic.
- **`frontend_site/`**: Contains the React frontend.
- **`backend/.env`**: Environment variables for the backend.
- **`frontend_site/.env`**: Environment variables for the frontend.

---

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/YourUsername/Multi_DiscordBot.git
cd Multi_DiscordBot
```
### 2. Backend Setup
#### 1. Create a virtual environment
```bash
cd backend
python -m venv venv
```
#### 2. Activate the environment
Windows:
```bash
venv\Scripts\activate
```
MacOs/Linux:
```bash
source venv/bin/activate
```
#### 3. Install the required python packages
```bash
pip install -r requirements.txt
```
#### 4. Create a .env and add the following information:
```bash
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_ANON_KEY=your_anon_key
FRONTEND_ORIGIN=http://localhost:3000
GEMINI_API_KEY=your_gemini_api_key
```
### 3. Frontend Setup
#### 1. Install the required packages
```bash
cd ../frontend_site
npm install
```
#### 2. Create a .env file with the following information:
```bash
REACT_APP_API_URL=http://localhost:5000
```

## Running the Project
### 1. Running the backend
```bash
cd backend
python app.py
```
### 2. Running the frontend
```bash
cd ../frontend_site
npm start
```


