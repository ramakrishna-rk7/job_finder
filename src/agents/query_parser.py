"""Query Parser - converts natural language to structured query."""

import os
import re
import json
from typing import List, Optional, Dict, Any
import httpx

from ..schemas.models import StructuredQuery
from ..config.settings import HF_TOKEN, HF_MODEL, USE_HF


QUERY_PARSER_SYSTEM_PROMPT = """You are a Query Parser Agent specialized in converting user job search requests into structured search parameters.

Your task is to extract from the user input:
1. keywords - Job titles/roles (e.g., "Python developer" → ["Python", "developer"])
2. location - City or country
3. remote - true/false for remote work
4. experience - fresher/junior/mid/senior

Examples:
Input: "Remote AI jobs for freshers in India"
Output: keywords: ["AI", "Machine Learning"], location: "India", remote: true, experience: "fresher"

Input: "Python developer jobs"
Output: keywords: ["Python", "developer"], location: null, remote: null, experience: null

Input: "Senior Data Scientist Bangalore"
Output: keywords: ["Data", "Scientist"], location: "Bangalore", remote: null, experience: "senior"

Input: "React WFH internship"
Output: keywords: ["React"], location: null, remote: true, experience: "fresher"

Input: "Full stack developer 10 LPA"
Output: keywords: ["Full", "stack", "developer"], location: null, remote: null, experience: null, salary_min: 10

Guidelines:
- Normalize synonyms: ML=Machine Learning, AI=Artificial Intelligence, WFH=remote
- Extract experience: fresher/intern/trainee → fresher, junior → junior, lead → senior"""


def parse_with_huggingface(prompt: str) -> StructuredQuery:
    """Parse using Hugging Face DeepSeek-R1."""
    if not HF_TOKEN or not HF_MODEL:
        raise ValueError("HF_TOKEN or HF_MODEL not configured")

    system_prompt = """You are a job search query parser. Convert user input to valid JSON with exactly this structure:
{
  "keywords": ["Python", "developer"],
  "location": "India" | null,
  "remote": true | false | null,
  "experience": "fresher" | "junior" | "mid" | "senior" | null,
  "salary_min": 10 | null
}

Return ONLY valid JSON, no explanation or markdown."""

    url = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}

    full_prompt = f"System: {system_prompt}\n\nUser: Convert this to JSON: {prompt}\nAssistant:"

    payload = {
        "inputs": full_prompt,
        "parameters": {
            "temperature": 0.3,
            "max_new_tokens": 512,
            "return_full_text": False
        }
    }

    with httpx.Client(timeout=120.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

        if isinstance(result, list) and len(result) > 0:
            text = result[0].get("generated_text", "")
        else:
            text = str(result)

        try:
            data = json.loads(text.strip())
        except:
            import re
            match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                return normalize_query(prompt)

        return StructuredQuery(
            keywords=data.get("keywords", []),
            location=data.get("location"),
            remote=data.get("remote"),
            experience=data.get("experience"),
            salary_min=data.get("salary_min")
        )


def parse_with_groq(prompt: str) -> StructuredQuery:
    """Parse using Groq."""
    from crewai import Agent, LLM, Task, Crew

    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY not configured")

    llm = LLM(
        model="groq/llama-3.3-70b-versatile",
        api_key=api_key,
        temperature=0.2,
        max_tokens=512
    )

    agent = Agent(
        role="Query Parser",
        goal="Convert user job request into structured search query",
        backstory="Extract keywords, location, remote, experience from job search queries.",
        llm=llm,
        output_pydantic=StructuredQuery,
        verbose=False
    )

    task = Task(
        description=f"Parse: {prompt}",
        agent=agent,
        expected_output="JSON with keywords, location, remote, experience"
    )

    crew = Crew(agents=[agent], tasks=[task], verbose=False)
    result = crew.kickoff()

    if hasattr(result, 'pydantic'):
        return result.pydantic
    return result


def normalize_query(prompt: str) -> StructuredQuery:
    """Fast rule-based parser (fallback)."""
    prompt_lower = prompt.lower()

    keywords = []
    role = None
    skills = []
    location = None
    remote = None
    experience = None
    salary_min = None
    freshness = 24

    location_map = {
        "india": "India", "bangalore": "Bangalore", "bengaluru": "Bangalore",
        "mumbai": "Mumbai", "delhi": "Delhi", "hyderabad": "Hyderabad",
        "chennai": "Chennai", "pune": "Pune", "kolkata": "Kolkata",
        "usa": "USA", "uk": "UK", "canada": "Canada", "germany": "Germany",
        "singapore": "Singapore", "dubai": "Dubai", "remote": None
    }

    remote_keywords = ["remote", "wfh", "work from home", "work from anywhere", "online"]
    for keyword in remote_keywords:
        if keyword in prompt_lower:
            remote = True
            break

    if "12 hour" in prompt_lower:
        freshness = 12
    elif "24 hour" in prompt_lower:
        freshness = 24
    elif "48 hour" in prompt_lower:
        freshness = 48

    exp_map = {
        "fresher": "fresher", "freshers": "fresher",
        "intern": "fresher", "internship": "fresher",
        "trainee": "fresher", "entry": "fresher",
        "junior": "junior", "jr": "junior",
        "mid": "mid", "intermediate": "mid",
        "senior": "senior", "sr": "senior", "lead": "senior", "principal": "senior"
    }

    exp_found = None
    for exp, level in exp_map.items():
        if exp in prompt_lower:
            exp_found = level
            break
    experience = exp_found

    salary_match = re.search(r'(\d+)\s*lpa', prompt_lower)
    if salary_match:
        salary_min = int(salary_match.group(1))

    words = prompt.split()
    for word in words:
        word_clean = word.lower().strip(',.!?')
        if word_clean in location_map and word_clean != "remote":
            location = location_map[word_clean]
            break

    stop_words = {
        "jobs", "job", "work", "hiring", "opening", "position",
        "india", "bangalore", "mumbai", "delhi", "hyderabad", "chennai", "pune",
        "remote", "wfh", "fresher", "freshers", "junior", "senior", "lead",
        "intern", "trainee", "mid", "internship", "last", "past", "hours", "days"
    }

    role_keywords = [
        "python", "java", "javascript", "typescript", "c++", "c#", "ruby", "go",
        "react", "angular", "vue", "node.js", "django", "flask", "fastapi",
        "sql", "mysql", "postgresql", "mongodb", "redis",
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
        "git", "jenkins", "ci/cd", "agile", "scrum",
        "machine learning", "deep learning", "tensorflow", "pytorch", "nlp",
        "html", "css", "rest api", "graphql",
        "linux", "bash", "shell scripting",
        "data analysis", "data science", "pandas", "numpy", "excel",
        "communication", "leadership", "problem solving", "teamwork"
    ]

    role_map = {
        "ai": "AI Engineer",
        "ml": "Machine Learning Engineer",
        "machine learning": "Machine Learning Engineer",
        "data science": "Data Scientist",
        "data analyst": "Data Analyst",
        "full stack": "Full Stack Developer",
        "frontend": "Frontend Developer",
        "backend": "Backend Developer",
        "web developer": "Web Developer",
        "devops": "DevOps Engineer",
    }

    for word in words:
        word_clean = word.lower().strip(',.!?')
        if word_clean in role_map:
            role = role_map[word_clean]
        if word_clean in role_keywords and word_clean not in stop_words:
            if word_clean == "ai":
                skills.extend(["Artificial Intelligence", "Machine Learning"])
            elif word_clean == "ml":
                skills.append("Machine Learning")
            elif word_clean == "data scientist":
                skills.append("Data Scientist")
            elif word_clean == "data analyst":
                skills.append("Data Analyst")
            elif word_clean == "full stack":
                skills.append("Full Stack")
            elif word_clean == "machine learning":
                skills.append("Machine Learning")
            elif word_clean == "deep learning":
                skills.append("Deep Learning")
            else:
                keywords.append(word.capitalize())

    if role and not keywords:
        keywords = [role]

    if not keywords:
        keywords = [prompt.strip().split()[0].capitalize()]

    return StructuredQuery(
        keywords=keywords,
        role=role,
        skills=skills,
        location=location,
        remote=remote,
        experience=experience,
        salary_min=salary_min,
        freshness=freshness
    )


def parse(prompt: str, use_ai: bool = False) -> StructuredQuery:
    """Parse user prompt - default to rule-based (fast/no API needed)."""
    return normalize_query(prompt)


if __name__ == "__main__":
    test_inputs = [
        "Remote AI jobs for freshers in India",
        "Python developer jobs",
        "Senior Data Scientist Bangalore",
        "React WFH internship",
    ]

    print("Testing Query Parser:\n")
    for prompt in test_inputs:
        try:
            result = parse(prompt)
            print(f"Input: {prompt}")
            print(f"Output: {result.model_dump_json()}\n")
        except Exception as e:
            print(f"Error: {e}")