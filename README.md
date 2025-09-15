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
create table public.user_jobs (
  id serial not null,
  user_id uuid null,
  job_name character varying(500) not null,
  company character varying(200) not null,
  location character varying(200) null,
  location_type character varying(50) null,
  job_type character varying(100) null,
  posting_date character varying(100) null,
  application_link text not null,
  description text null,
  source character varying(50) null default 'linkedin'::character varying,
  scraped_at timestamp with time zone null default now(),
  created_at timestamp with time zone null default now(),
  application_status character varying(20) null default 'not_applied'::character varying,
  status_updated_at timestamp with time zone null default now(),
  constraint user_jobs_pkey primary key (id),
  constraint user_jobs_application_link_key unique (application_link),
  constraint user_jobs_user_id_application_link_key unique (user_id, application_link),
  constraint user_jobs_user_id_fkey foreign KEY (user_id) references auth.users (id) on delete CASCADE
) TABLESPACE pg_default;

create index IF not exists idx_user_jobs_user_id on public.user_jobs using btree (user_id) TABLESPACE pg_default;

create index IF not exists idx_user_jobs_application_link on public.user_jobs using btree (application_link) TABLESPACE pg_default;

create index IF not exists idx_user_jobs_company_name on public.user_jobs using btree (company, job_name) TABLESPACE pg_default;

create index IF not exists idx_user_jobs_status on public.user_jobs using btree (application_status) TABLESPACE pg_default;

create index IF not exists idx_user_jobs_status_updated on public.user_jobs using btree (status_updated_at) TABLESPACE pg_default;
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

