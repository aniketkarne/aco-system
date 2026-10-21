"""
LLM Client - Unified interface for different LLM providers.
Supports: OpenAI, Anthropic, X.AI (Grok), and Mock for testing
"""
import json
import time
import logging
import re
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
import httpx

from config.settings import get_settings


# ---------------------------------------------------------------------------
# Agent prompt/response logger — write all LLM traffic to agents.log
# ---------------------------------------------------------------------------

def _build_agent_logger():
    """Get (or create) the agents.log logger. Thread-safe, called once per provider."""
    logger = logging.getLogger("agents")
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler("agents.log")
    handler.setLevel(logging.DEBUG)
    # Compact format: just timestamp and content
    formatter = logging.Formatter(
        "%(asctime)s  %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def _prompt_summary(messages: List[Dict], max_chars: int = 800) -> str:
    """One-line summary of the prompt for the log header."""
    lines = []
    for msg in messages:
        role = msg.get("role", "???")
        content = msg.get("content", "")
        # Collapse whitespace, truncate
        text = " ".join(content.split())[:max_chars]
        lines.append(f"[{role}] {text}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Model-capability helpers
#
# Provider APIs have tightened over time, and the old hardcoded model IDs in
# this file were several generations stale. These helpers encode the current
# rules so a payload never contains a parameter the target model rejects.
# ---------------------------------------------------------------------------

# OpenAI reasoning models: gpt-5+, gpt-6, and the o-series. They reject
# temperature/top_p unless reasoning effort is "none", and they take
# max_completion_tokens rather than max_tokens.
_OPENAI_REASONING_MODEL_RE = re.compile(r"^(gpt-5|gpt-6|o1|o3|o4)")


def _is_openai_reasoning_model(model: str) -> bool:
    """True if the model is an OpenAI reasoning model."""
    return bool(_OPENAI_REASONING_MODEL_RE.match((model or "").lower()))


# Anthropic retired temperature/top_p/top_k on Claude 4.7 and later: sending
# a non-default value returns HTTP 400. Model IDs look like
# "claude-opus-5-5", "claude-sonnet-4-6", "claude-3-5-haiku-20241022".
_ANTHROPIC_VERSION_RE = re.compile(r"^claude-(?:opus|sonnet|haiku|fable|mythos)-(\d+)(?:-(\d+))?")


def _anthropic_rejects_sampling_params(model: str) -> bool:
    """True if the Claude model rejects temperature/top_p/top_k.

    Claude 4.7 and later (including the 5.x family) reject a non-default
    sampling temperature with HTTP 400. Older models still accept it.
    """
    match = _ANTHROPIC_VERSION_RE.match((model or "").lower())
    if not match:
        return False

    major = int(match.group(1))
    minor = int(match.group(2)) if match.group(2) else 0

    # 3.x and 4.0-4.6 accept temperature; 4.7+ does not.
    return major >= 5 or (major == 4 and minor >= 7)


class LLMClient(ABC):
    """Base LLM client interface.

    Every provider must accept the same keyword arguments, because
    ``LoggingProxyLLMClient`` forwards ``model`` (and callers may pass
    ``max_tokens``) to whatever client is wrapped. A provider that omits
    ``**kwargs`` raises ``TypeError`` before the request is ever sent.
    """

    @abstractmethod
    def chat(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Send chat messages and get response.

        Args:
            messages: Chat messages.
            temperature: Sampling temperature. Providers that reject it
                (current Anthropic/OpenAI reasoning models) ignore it.
            model: Per-call model override. Falls back to the client default.
            max_tokens: Output token cap. Falls back to the client default.
        """
        pass

    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for cost tracking."""
        pass


class MockLLMClient(LLMClient):
    """Mock LLM client for testing without API keys."""

    def __init__(self, mock_responses: Optional[Dict] = None):
        self.mock_responses = mock_responses or {}
        self.pm_questions_asked = False  # Track if PM asked questions

    def chat(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Generate mock responses based on conversation context."""
        user_msg = ""
        system_msg = ""
        conversation_history = ""

        # Get context
        for msg in messages:
            if msg["role"] == "user":
                user_msg = msg["content"].lower()
            if msg["role"] == "system":
                system_msg = msg["content"].lower()
            # Track conversation
            if msg["role"] in ["user", "assistant"]:
                conversation_history += msg["content"][:200].lower() + " "

        # Connection test
        if "ok" in user_msg or "confirm connection" in user_msg:
            return "OK"

        # PM mock response (questions and refinement)
        if "pm" in system_msg or "project manager" in system_msg or "requirements gathering" in system_msg:

            # Check if we already asked questions (look for past responses)
            if "clarifying questions" in conversation_history:
                # We already asked, check for answers or skip
                if "skip" in user_msg or "proceed" in user_msg or "ready" in user_msg or "that's fine" in user_msg:
                    self.pm_questions_asked = False  # Reset
                    return """## ✅ Requirements Confirmed

Thanks for your answers! I'm ready to finalize this story.

Here's the refined scope for CarInterview:

**Target Users**:
- Job seekers with interviews in next 24-48 hours
- Students and career changers

**Core Features (MVP)**:
1. Resume upload & parsing (PDF/DOCX, extract skills/experience)
2. Job description input & key requirement extraction
3. Basic company research (company name, size, tech stack)
4. 10-15 minute voice mock interviews (behavioral + technical)
5. AI-adaptive questions based on resume + JD match
6. Feedback report (confidence, clarity, relevance, suggestions)

**Tech Stack (MVP)**:
- Flutter for mobile (iOS + Android)
- FastAPI backend
- Firebase Auth (email/password + social login)
- SQLite database (for MVP simplicity)
- RevenueCat for payments ($9.99/month subscription)
- Deepgram + GPT-4 for voice AI
- AWS hosting (EC2)

**Monetization**:
- 3 free interviews, then $9.99/month unlimited
- No annual discount for v1

**Success Metrics**:
- 100 users in first month
- 20% conversion to paid
- 4.5+ star rating

**Out of Scope (v2)**:
- Video interviews
- Deep company research (Glassdoor, reviews, culture)
- Technical/coding interviews

---

Moving to **planner** for task breakdown. The planner will:
- Break this into 30-50 atomic, testable tasks
- Estimate each task (1-16 hours)
- Identify dependencies between tasks
- Create technical specifications

Estimated total effort: 120-160 hours (3-4 weeks)

✅ **Story finalized. Ready for planner.**"""
                else:
                    # User answered some questions but not all
                    return """Thanks for your answers! A few more clarifications needed:

**Still need answers for**:
1. Interview duration (5, 10, 15, or 30 minutes?)
2. Video or audio-only interviews?
3. When should interviews expire from the free tier?

Reply with answers or say "skip" to proceed with defaults."""

            # First time - ask all questions
            return """## 📋 Story Analysis: CarInterview

I've reviewed your CarInterview concept. Strong vision!

### What I Understand:

**Core Concept**: A mobile app for practicing job interviews right before walking in.

**Value Prop**: Low-pressure, realistic practice when stakes are highest (driving to interview).

**Proposed Tech Stack**:
- Flutter (iOS + Android)
- FastAPI backend
- Firebase Auth
- SQLite → MySQL later
- RevenueCat subscriptions
- Deepgram + GPT-4 voice AI
- AWS hosting

---

## 🤔 Clarifying Questions for CarInterview

I need to understand a few things before planning:

### Product & Target Users
1. **Who's your PRIMARY target user?**
   - Students preparing for campus interviews?
   - Career changers pivoting industries?
   - Recent grads (0-2 years experience)?
   - Seasoned professionals (3+ years)?

2. **When EXACTLY do they use this?**
   - In the car driving to the interview (5-10 min before)?
   - At home, day before?
   - Week of leading up?

3. **Interview duration target?**
   - 5 min (quick practice)?
   - 10-15 min (realistic)?
   - 30 min (thorough)?

### Features & Scope
4. **Resume parsing depth?**
   - Auto-extract skills & experience (harder, needs ML)?
   - Just store & display (easier for MVP)?

5. **Company research depth?**
   - Basic: company name, size, tech stack (easy)?
   - Deep: Glassdoor reviews, common questions, culture (harder)?

6. **Video or audio?**
   - Audio-only interviews?
   - Video interviews too?
   - Why/why not?

7. **Interview question types?**
   - Behavioral only ("Tell me about a time...")?
   - Technical/coding too?
   - Both (configurable)?

### Monetization
8. **Free tier details?**
   - 3 free interviews total?
   - 3 per month?
   - 7-day trial?

9. **What happens after free tier?**
   - Hard block until subscribe?
   - Show preview, blur interview?

10. **Pricing confirmation?**
    - $9.99/month for unlimited?
    - Any annual discount ($89/year)?
    - Enterprise tier later?

### Technical Decisions
11. **Voice AI provider choice?**
    - Deepgram + GPT-4 (real-time, more expensive)?
    - ElevenLabs Conversational AI (easier setup)?

12. **Firebase scope?**
    - Auth only?
    - Or Firestore too (interview history storage)?

13. **Database for MVP?**
    - SQLite (simpler, no server needed)?
    - MySQL from start?

### Launch & MVP Scope
14. **What's ABSOLUTE minimum for v1?**
    - Can we drop: company research? video? technical questions?

15. **Launch timeline?**
    - 1 month (aggressive)?
    - 3 months (realistic)?

16. **Budget constraints?**
    - Monthly LLM/API budget limit?
    - Any cost concerns?

17. **Success metrics?**
    - 100 users month 1?
    - 20% conversion to paid?
    - 4.5+ star rating?

---

**Reply with:**
- Answers to numbered questions (1-17), OR
- "skip" - I'll proceed with reasonable defaults based on your original description

Once finalized, I'll create a detailed PRD and hand to planner for task breakdown."""

        # Architect mock response (approval/rejection)
        if "architect" in system_msg or "feasibility" in system_msg or "technical review" in system_msg:
            return """{
  "approved": true,
  "reasoning": "Mock response for testing - story looks complete",
  "risks": [],
  "recommendations": [],
  "missing_tasks": [],
  "technical_guidance": "No concerns - proceed with development"
}"""

        # Planner mock response (task breakdown)
        if "planner" in system_msg or "break down" in system_msg or "atomic tasks" in system_msg:
            # Check what story we're planning
            if "carinterview" in user_msg or "mobile mock interview" in user_msg or "flutter" in user_msg:
                # CarInterview-specific tasks
                return """{
  "tasks": [
    {
      "title": "Set up Flutter project structure",
      "description": "Initialize Flutter project, configure dependencies, set up folder structure for lib/, test/, android/, ios/",
      "estimate_hours": 4,
      "dependencies": [],
      "technical_notes": "Use Flutter CLI, follow pub.dev conventions"
    },
    {
      "title": "Design Firebase authentication flow",
      "description": "Configure Firebase Auth for email/password and Google sign-in, set up user profile schema",
      "estimate_hours": 6,
      "dependencies": [1],
      "technical_notes": "Use firebase_auth package, handle auth state changes"
    },
    {
      "title": "Create FastAPI backend structure",
      "description": "Set up FastAPI project, configure Pydantic models, CORS, middleware, health endpoint",
      "estimate_hours": 5,
      "dependencies": [],
      "technical_notes": "Use FastAPI, uvicorn, follow project structure best practices"
    },
    {
      "title": "Implement resume upload endpoint",
      "description": "Create POST /api/resume endpoint, validate PDF/DOCX files, extract text content",
      "estimate_hours": 8,
      "dependencies": [3],
      "technical_notes": "Use python-multipart for file uploads, PyPDF2 or docx2txt for parsing"
    },
    {
      "title": "Build resume parsing service",
      "description": "Extract skills, experience, education from resume text, store in SQLite database",
      "estimate_hours": 12,
      "dependencies": [4],
      "technical_notes": "Use NLP or regex patterns, normalize skill data"
    },
    {
      "title": "Implement job description input",
      "description": "Create UI for pasting JD or entering URL, extract key requirements and skills",
      "estimate_hours": 6,
      "dependencies": [],
      "technical_notes": "Flutter TextField, auto-extract keywords"
    },
    {
      "title": "Add company research service",
      "description": "Integrate with company data API, fetch company size, tech stack, description",
      "estimate_hours": 10,
      "dependencies": [3],
      "technical_notes": "Use public APIs (Crunchbase, LinkedIn), store in database"
    },
    {
      "title": "Build Deepgram voice integration",
      "description": "Set up Deepgram WebSocket for real-time speech-to-text, handle audio permissions",
      "estimate_hours": 12,
      "dependencies": [],
      "technical_notes": "Use deepgram_flutter package, request microphone permission"
    },
    {
      "title": "Connect LLM for interview questions",
      "description": "Send transcript + resume + JD to GPT-4, generate adaptive interview questions",
      "estimate_hours": 8,
      "dependencies": [4, 5, 6, 7, 8],
      "technical_notes": "Use OpenAI API, prompt engineer for contextual questions"
    },
    {
      "title": "Build interview flow UI",
      "description": "Create Flutter screens for interview start, real-time question display, answer recording, interview summary",
      "estimate_hours": 16,
      "dependencies": [8, 9],
      "technical_notes": "State management (Provider/GetX), responsive design"
    },
    {
      "title": "Implement interview feedback system",
      "description": "Generate feedback report (confidence, clarity, relevance), save to database, display to user",
      "estimate_hours": 10,
      "dependencies": [9, 10],
      "technical_notes": "Score responses, provide suggestions for improvement"
    },
    {
      "title": "Integrate RevenueCat subscriptions",
      "description": "Configure RevenueCat SDK, set up pricing ($9.99/month), manage entitlements (3 free vs unlimited)",
      "estimate_hours": 8,
      "dependencies": [1],
      "technical_notes": "Handle purchase events, validate entitlements before interview"
    },
    {
      "title": "Set up SQLite database",
      "description": "Design and implement database schema for users, resumes, interviews, companies, subscriptions",
      "estimate_hours": 6,
      "dependencies": [3],
      "technical_notes": "Use SQLite3 or sqflite, migrate to MySQL later"
    },
    {
      "title": "Build user settings and profile screens",
      "description": "Create Flutter UI for profile management, subscription status, interview history",
      "estimate_hours": 8,
      "dependencies": [2, 12, 13],
      "technical_notes": "SharedPreferences for local storage, Firebase Auth for profile"
    },
    {
      "title": "Implement free tier counter",
      "description": "Track interview count (3 free), enforce paywall, show upgrade prompt",
      "estimate_hours": 4,
      "dependencies": [11, 13],
      "technical_notes": "Check RevenueCat entitlements, display paywall"
    },
    {
      "title": "Add error handling and edge cases",
      "description": "Handle network errors, audio permission denied, LLM failures, subscription validation",
      "estimate_hours": 6,
      "dependencies": [9, 10, 11],
      "technical_notes": "Graceful degradation, user-friendly error messages"
    },
    {
      "title": "Write unit tests for Flutter app",
      "description": "Test auth flow, interview flow, UI components using Flutter test framework",
      "estimate_hours": 12,
      "dependencies": [1, 2, 9],
      "technical_notes": "Widget tests, integration tests, test coverage > 70%"
    },
    {
      "title": "Write API tests for backend",
      "description": "Test resume parsing, job extraction, company research endpoints using pytest",
      "estimate_hours": 8,
      "dependencies": [3, 4, 5, 6, 7],
      "technical_notes": "Unit tests, mock external APIs (Deepgram, GPT-4)"
    },
    {
      "title": "Deploy backend to AWS",
      "description": "Set up EC2 instance, configure uvicorn, set up environment variables, deploy FastAPI",
      "estimate_hours": 4,
      "dependencies": [3, 18],
      "technical_notes": "Use AWS Elastic Beanstalk or EC2, set up CI/CD"
    },
    {
      "title": "Build iOS app and test on device",
      "description": "Compile Flutter to iOS, configure signing, test on iPhone simulator and real device",
      "estimate_hours": 8,
      "dependencies": [1, 9, 17],
      "technical_notes": "Xcode configuration, App Store testing, iOS permissions"
    },
    {
      "title": "Build Android app and test on device",
      "description": "Compile Flutter to Android, configure signing, test on emulator and real device",
      "estimate_hours": 8,
      "dependencies": [1, 9, 17],
      "technical_notes": "Gradle configuration, Google Play testing, Android permissions"
    }
  ],
  "total_estimate_hours": 165,
  "critical_path": [1, 2, 3, 4, 5, 8, 9, 10, 11, 17, 20, 21],
  "risks": [
    "Deepgram API costs for real-time transcription",
    "GPT-4 API costs for interview generation",
    "Audio permission handling on iOS/Android",
    "RevenueCat integration complexity"
  ]
}"""
            else:
                # Default generic tasks (for login example)
                return """{
  "tasks": [
    {
      "title": "Set up project structure and dependencies",
      "description": "Initialize Flutter project, install required packages, set up project structure",
      "estimate_hours": 2,
      "dependencies": [],
      "technical_notes": "Use poetry or pip, follow FastAPI project structure best practices"
    },
    {
      "title": "Design database schema for users table",
      "description": "Create User model with email, password_hash, created_at, updated_at fields",
      "estimate_hours": 3,
      "dependencies": [1],
      "technical_notes": "Use SQLAlchemy ORM, include password hashing logic"
    },
    {
      "title": "Implement user registration endpoint",
      "description": "Create POST /register endpoint with email and password validation",
      "estimate_hours": 4,
      "dependencies": [2],
      "technical_notes": "Use Pydantic models for validation, bcrypt for password hashing"
    },
    {
      "title": "Implement user login endpoint",
      "description": "Create POST /login endpoint, validate credentials, return JWT token",
      "estimate_hours": 4,
      "dependencies": [3],
      "technical_notes": "Use JWT for sessions, implement proper error handling"
    },
    {
      "title": "Add password hashing utility",
      "description": "Create utility function to hash passwords using bcrypt",
      "estimate_hours": 2,
      "dependencies": [2],
      "technical_notes": "Use bcrypt library, configure proper rounds"
    },
    {
      "title": "Add JWT token generation and validation",
      "description": "Create JWT utilities for generating and validating tokens",
      "estimate_hours": 3,
      "dependencies": [4],
      "technical_notes": "Use PyJWT library, set reasonable expiration time"
    },
    {
      "title": "Write unit tests for auth endpoints",
      "description": "Test registration, login, and token validation",
      "estimate_hours": 4,
      "dependencies": [4, 6],
      "technical_notes": "Use pytest, test success and error cases"
    }
  ],
  "total_estimate_hours": 22,
  "critical_path": [1, 2, 3, 4, 6],
  "risks": ["Need to handle concurrent logins", "Token revocation not implemented in MVP"]
}"""

        # QA mock response
        if "qa" in system_msg or "testing" in system_msg or "test cases" in system_msg:
            return """{
  "tests_passed": true,
  "tests_run": 15,
  "test_results": {
    "unit_tests": 12,
    "integration_tests": 3,
    "failed": 0
  },
  "bugs_found": [],
  "reasoning": "Mock response for testing - story looks complete",
  "recommendations": ["Add more edge case tests", "Consider load testing"]
}"""

        # Default mock response
        return """{
  "approved": true,
  "reasoning": "Mock response for testing - story looks complete",
  "risks": [],
  "recommendations": []
}"""

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate."""
        return len(text) // 4


class LoggingProxyLLMClient(LLMClient):
    """
    Thin decorator around any LLMClient that logs every prompt → response
    to agents.log so you can `tail -f agents.log` and watch agents think.
    """

    def __init__(self, wrapped: LLMClient, agent_name: str = "agent", agent_model: str = None):
        self._wrapped = wrapped
        self._agent_name = agent_name
        self._agent_model = agent_model  # per-agent model override
        self._logger = _build_agent_logger()
        self._call_count = 0

    def chat(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        # Inject per-agent model if set and not overridden by caller
        if model is None and self._agent_model:
            model = self._agent_model
        self._call_count += 1
        call_id = f"{self._agent_name}#{self._call_count}"
        prompt = _prompt_summary(messages)

        self._logger.debug(f"\n{'='*60}\n--> [{call_id}] PROMPT\n{prompt}\n{'='*60}")

        start = time.time()
        response = self._wrapped.chat(
            messages,
            temperature=temperature,
            model=model,
            max_tokens=max_tokens,
            **kwargs,
        )
        elapsed = time.time() - start

        # Log response — first 300 chars as preview, full at DEBUG
        preview = response[:300].replace("\n", " ")
        self._logger.debug(f"\n<-- [{call_id}] RESPONSE ({elapsed:.1f}s)\n{response}\n")
        self._logger.debug(f"\n<-- [{call_id}] RESPONSE ({elapsed:.1f}s) [preview] {preview}...")

        return response

    def estimate_tokens(self, text: str) -> int:
        return self._wrapped.estimate_tokens(text)



class XAIClient(LLMClient):
    """X.AI (Grok) client."""

    def __init__(self, api_key: str, model: str = "grok-4.7"):
        self.api_key = api_key
        self.base_url = "https://api.x.ai/v1"
        # grok-beta is no longer published in the xAI model catalog.
        self.model = model
        self.session = httpx.Client(timeout=60.0)

    def chat(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Send chat to X.AI Grok."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "messages": messages,
            "model": model or self.model,
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

        except httpx.HTTPError as e:
            raise RuntimeError(f"X.AI API error: {e}")

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate (4 chars ≈ 1 token for English)."""
        return len(text) // 4


class OpenAIClient(LLMClient):
    """OpenAI client."""

    def __init__(self, api_key: str, model: str = "gpt-6.1-sol"):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"
        # gpt-4-turbo-preview is deprecated; gpt-6.1-sol is the current
        # balanced-intelligence model in the gpt-6 family.
        self.model = model
        self.session = httpx.Client(timeout=60.0)

    def chat(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        resolved_model = model or self.model
        payload = {
            "messages": messages,
            "model": resolved_model,
            "stream": False,
        }

        if _is_openai_reasoning_model(resolved_model):
            # Reasoning models (gpt-5+, gpt-6, o-series) reject temperature
            # and top_p unless the reasoning effort is "none", and they take
            # max_completion_tokens instead of max_tokens.
            #
            # We do not force an effort: the caller's requested effort wins if
            # given, otherwise the provider default applies. Note that some
            # current models (e.g. gpt-6.1-sol) reject effort="none"
            # outright, so sending it unasked would itself 400.
            effort = kwargs.get("reasoning_effort")
            if effort is not None:
                payload["reasoning_effort"] = effort
            if effort == "none":
                payload["temperature"] = temperature
            if max_tokens:
                payload["max_completion_tokens"] = max_tokens
        else:
            payload["temperature"] = temperature
            if max_tokens:
                payload["max_tokens"] = max_tokens

        response = self.session.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4


class AnthropicClient(LLMClient):
    """Anthropic Claude client."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-5-5"):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1"
        # claude-3-sonnet-20240229 is retired; claude-sonnet-5-5 is the
        # current general-purpose model.
        self.model = model
        self.session = httpx.Client(timeout=60.0)

    def chat(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        # Anthropic uses different format
        system_message = ""
        chat_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                chat_messages.append(msg)

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        resolved_model = model or self.model
        payload = {
            "model": resolved_model,
            "max_tokens": max_tokens or get_settings().MAX_TOKENS,
            "system": system_message,
            "messages": chat_messages,
        }

        # Claude 4.7+ (incl. the 5.x family) rejects temperature/top_p/top_k
        # with a 400 unless the value is the default, so we only send
        # temperature for older models that still accept it.
        if not _anthropic_rejects_sampling_params(resolved_model):
            payload["temperature"] = temperature

        response = self.session.post(
            f"{self.base_url}/messages",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4


class MinimaxClient(LLMClient):
    """MiniMax client - OpenAI-compatible API via minimax.io."""

    def __init__(self, api_key: str, model: str = "MiniMax-M3"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://www.minimax.io/v1"
        self.session = httpx.Client(timeout=120.0)

    def chat(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model or self.model,
            "messages": messages,
            # MiniMax-M3 / M3.1-Flash always use temperature 1 and ignore the
            # parameter; sending it is a no-op rather than an error, but
            # top_p must stay in (0, 1] when sent.
            "max_completion_tokens": max_tokens or get_settings().MAX_TOKENS,
        }

        response = self.session.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
        )

        if response.status_code != 200:
            error_body = response.text[:1000]
            raise Exception(f"MiniMax API error {response.status_code}: {error_body}")

        data = response.json()
        return data["choices"][0]["message"]["content"]

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4


class OpenRouterClient(LLMClient):
    """OpenRouter client - unified API for multiple LLM providers."""

    def __init__(self, api_key: str, model: str = "minimax/minimax-m3",
                 referer: str = "https://github.com/aco-system/aco-system",
                 title: str = "ACO System"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"
        self.session = httpx.Client(timeout=120.0)
        self.referer = referer
        self.title = title

    def chat(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Send chat messages via OpenRouter."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.referer,
            "X-Title": self.title,
        }

        payload = {
            "model": model or self.model,
            "messages": messages,
            "max_tokens": max_tokens or get_settings().MAX_TOKENS,
        }

        response = self.session.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
        )

        if response.status_code != 200:
            error_body = response.text[:1000]
            raise Exception(f"OpenRouter API error {response.status_code}: {error_body}")

        data = response.json()
        return data["choices"][0]["message"]["content"]

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4


def get_llm_client() -> LLMClient:
    """Get the configured LLM client."""
    settings = get_settings()

    # Check for mock mode first (for testing)
    if settings.LLM_PROVIDER == "mock":
        return MockLLMClient()

    if settings.LLM_PROVIDER == "xai":
        if not settings.XAI_API_KEY:
            raise ValueError("XAI_API_KEY not configured")
        return XAIClient(settings.XAI_API_KEY, settings.XAI_MODEL)

    elif settings.LLM_PROVIDER == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured")
        return OpenAIClient(settings.OPENAI_API_KEY, settings.OPENAI_MODEL)

    elif settings.LLM_PROVIDER == "anthropic":
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not configured")
        return AnthropicClient(settings.ANTHROPIC_API_KEY, settings.ANTHROPIC_MODEL)

    elif settings.LLM_PROVIDER == "openrouter":
        if not settings.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not configured")
        return OpenRouterClient(settings.OPENROUTER_API_KEY, settings.OPENROUTER_MODEL)

    elif settings.LLM_PROVIDER == "minimax":
        if not settings.MINIMAX_API_KEY:
            raise ValueError("MINIMAX_API_KEY not configured")
        return MinimaxClient(settings.MINIMAX_API_KEY, settings.MINIMAX_MODEL)

    else:
        raise ValueError(f"Unknown LLM provider: {settings.LLM_PROVIDER}")


# Per-(agent_name, model) client cache — avoids global mutation
# Key: (agent_name, model) → LoggingProxyLLMClient instance
_llm_client_cache: dict = {}


def get_client(agent_name: str = None) -> LLMClient:
    """
    Get or create a per-agent LLM client, wrapped so all prompts/responses
    go to agents.log.

    Each agent gets its own client instance keyed by (agent_name, model).
    This avoids the previous bug where a shared global client had its
    _agent_model mutated by subsequent callers, causing wrong models to be used.

    Pass agent_name so logs show e.g. 'architect#1' instead of generic 'agent#1'.
    """
    # Resolve agent model from settings
    agent_model = None
    if agent_name:
        try:
            from core.prompt_loader import (
                get_agent_model,
                get_agent_model_override,
                resolve_agent_name,
            )
            resolved_name = resolve_agent_name(agent_name)

            # An explicit per-agent override (ACO_*_MODEL) is deliberate, so
            # it is honoured for any provider.
            agent_model = get_agent_model_override(resolved_name)

            if agent_model is None:
                # The shared tiers (MODEL_OPU / MODEL_SONNET / MODEL_HAIKU)
                # are Anthropic model IDs. Injecting them into another
                # provider would send a model that provider does not know,
                # so only Anthropic uses them; every other provider falls
                # back to its own configured default model.
                from config.settings import get_settings
                if get_settings().LLM_PROVIDER == "anthropic":
                    agent_model = get_agent_model(agent_name)

            if agent_model == "none":
                agent_model = None
        except Exception:
            agent_model = None  # Fallback if prompt_loader fails

    cache_key = (agent_name, agent_model)

    if cache_key not in _llm_client_cache:
        raw = get_llm_client()
        _llm_client_cache[cache_key] = LoggingProxyLLMClient(
            raw,
            agent_name=agent_name or "agent",
            agent_model=agent_model,
        )

    return _llm_client_cache[cache_key]


def reset_client():
    """Reset all cached clients (useful for testing)."""
    global _llm_client_cache
    _llm_client_cache = {}
