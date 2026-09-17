#!/usr/bin/env python3
"""
Initialize ACO database and create an example story.
"""
import sys
from pathlib import Path

# Allow running from any cwd: add the directory containing this script.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.database import init_database, get_session, Story, StoryStatus
from config.settings import get_settings
from datetime import datetime


def main():
    """Initialize database and create story."""
    print("Initializing ACO database...")

    # Initialize database first
    settings = get_settings()
    init_database(settings.DATABASE_URL)
    print("✓ Database initialized")

    # Get session
    session = get_session()

    # Check if story already exists
    existing = session.query(Story).filter(Story.title == "AI Mock Interview App - Full Platform Development").first()
    if existing:
        print("⚠️  Story already exists, skipping...")
        session.close()
        return

    # Create new story
    story = Story(
        title="AI Mock Interview App - Full Platform Development",
        description="""AI-powered mock interview platform that helps job seekers prepare for real interviews.

**Core Features (MVP):**
1. Resume upload & parsing (PDF/DOCX, extract skills/experience)
2. Job description input & key requirement extraction
3. Company research (company name, size, tech stack)
4. 10-15 minute voice mock interviews (behavioral + technical)
5. AI-adaptive questions based on resume + JD match
6. Feedback report (confidence, clarity, relevance, suggestions)

**Tech Stack:**
- Flutter (iOS + Android mobile)
- Python + FastAPI (backend)
- Firebase Auth (email/password + Google sign-in)
- MySQL (database)
- OpenRouter API (minimax/minimax-m2.5 for questions)
- ChatGPT Realtime API (voice interview interface)
- RevenueCat ($9.99/month subscription)

**Success Metrics:**
- 100 users in first month
- 20% conversion to paid
- 4.5+ star rating""",
        status=StoryStatus.PM_REVIEW,
        priority="high",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        context_json={
            "github_issue_number": 1,
            "github_issue_url": f"https://github.com/{settings.GITHUB_OWNER}/{settings.GITHUB_REPO}/issues/1",
            "project_title": settings.GITHUB_REPO,
            "tech_stack": {
                "frontend": "Flutter (iOS + Android)",
                "backend": "Python + FastAPI",
                "auth": "Firebase Auth",
                "database": "MySQL",
                "ai_provider": "OpenRouter (minimax/minimax-m2.5)",
                "voice_provider": "ChatGPT Realtime API",
                "payments": "RevenueCat"
            },
            "features": [
                "Resume upload & parsing",
                "Job description input",
                "Company research",
                "AI mock interviews (voice)",
                "Feedback reports"
            ]
        },
        acceptance_criteria=[
            "Users can upload resumes (PDF/DOCX)",
            "System extracts skills from resume",
            "Users can paste job descriptions",
            "System researches companies",
            "AI conducts voice interviews (10-15 min)",
            "System provides detailed feedback reports",
            "Users can subscribe ($9.99/month)",
            "App runs on iOS and Android"
        ]
    )

    session.add(story)
    session.commit()

    print(f"✓ Story created with ID: {story.id}")
    print(f"✓ Title: {story.title}")
    print(f"✓ Status: {story.status.value}")
    print(f"✓ GitHub Issue: #{story.context_json['github_issue_number']}")
    print("\n📋 Story is ready for PM agent to process!")
    print("\nNext steps:")
    print("1. Run PM agent: python3 agents/project_manager.py")
    print("2. PM will ask clarifying questions if needed")
    print("3. PM will finalize story and hand to planner")
    print("4. Planner will break into tasks")
    print("5. Architect will review and approve")
    print("6. Dev agent will implement")
    print("7. QA agent will test")
    print("8. Human reviewer will approve")

    session.close()


if __name__ == "__main__":
    main()
