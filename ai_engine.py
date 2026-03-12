import os
import re
import subprocess

# name of the ollama model to use (must be installed locally or accessible via ollama)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")
MIN_BODY_WORDS = int(os.getenv("MIN_COLD_EMAIL_WORDS", "130"))


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences that may appear in CLI output."""
    return re.sub(r"\x1B\[[0-?]*[ -/]*[@-~]", "", text or "")


def _ascii_safe(text: str) -> str:
    """Normalize generated text so SMTP headers/body stay portable."""
    return (text or "").encode("ascii", "ignore").decode("ascii").strip()


def _lead_value(lead: dict, key: str, default: str) -> str:
    value = str(lead.get(key, "") or "").strip()
    return value if value else default


def _build_prompt(lead: dict) -> str:
    name = _lead_value(lead, "name", "there")
    company = _lead_value(lead, "company", "your business")
    solution = _lead_value(lead, "niche", "digital growth")
    industry = _lead_value(lead, "industry", "your industry")

    return (
        "Write a detailed B2B cold outreach email with real market-context language.\n"
        f"Recipient Name: {name}\n"
        f"Company: {company}\n"
        f"Solution We Provide: {solution}\n"
        f"Industry: {industry}\n\n"
        "Hard requirements:\n"
        "1) First line must be exactly in this format: Subject: <text>\n"
        "2) Then write the body with 5-7 short paragraphs and greeting.\n"
        "3) Include these ideas in order:\n"
        "   - personalized opener about their company/industry\n"
        "   - how the market is behaving now (competition, buyer behavior, demand shifts)\n"
        "   - common revenue/growth bottleneck for this segment\n"
        "   - how our solution solves it with two concrete outcomes\n"
        "   - soft CTA for a 15-minute call\n"
        "4) Keep total body length between 140 and 220 words.\n"
        "5) Avoid generic filler. Do not use placeholders like [Name].\n"
        "6) Output plain email text only, no markdown or bullet lists.\n"
        "7) Use ASCII only and do not use emoji.\n"
        f"8) Must include the exact phrase '{solution}' once in subject and at least once in body.\n"
        "9) Do not propose any other primary service."
    )


def _generate_with_ollama(prompt: str) -> tuple[str, str]:
    """Try ollama run first, then legacy generate command for compatibility."""
    commands = [
        ["ollama", "run", OLLAMA_MODEL, prompt],
        ["ollama", "generate", OLLAMA_MODEL, "--prompt", prompt],
    ]
    errors = []

    for cmd in commands:
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=True,
            )
            return _strip_ansi(proc.stdout).strip(), ""
        except FileNotFoundError as exc:
            errors.append(f"{' '.join(cmd[:3])}: {exc}")
            break
        except subprocess.CalledProcessError as exc:
            stderr = _strip_ansi(exc.stderr).strip()
            errors.append(f"{' '.join(cmd[:3])}: {stderr or str(exc)}")

    return "", " | ".join(errors)


def _normalize_email(raw_text: str, lead: dict) -> str:
    name = _lead_value(lead, "name", "there")
    solution = _lead_value(lead, "niche", "digital growth")
    industry = _lead_value(lead, "industry", "your industry")
    lines = [line.rstrip() for line in (raw_text or "").splitlines()]
    lines = [line for line in lines if line.strip()]

    if not lines:
        return _detailed_fallback(lead)

    first = _ascii_safe(lines[0].strip())
    if first.lower().startswith("subject:"):
        subject = first
        body_lines = lines[1:]
    else:
        subject = f"Subject: Growth strategy opportunity for {solution} in {industry}"
        body_lines = lines

    if not body_lines:
        return _detailed_fallback(lead)

    body = _ascii_safe("\n".join(body_lines).strip())
    if not body.lower().startswith("hi "):
        body = f"Hi {name},\n\n{body}"

    # If model returns very short content, fall back to a detailed template.
    body_word_count = len(body.split())
    if body_word_count < MIN_BODY_WORDS:
        return _detailed_fallback(lead)
    final_text = _ascii_safe(f"{subject}\n{body}")
    if not _solution_alignment_ok(final_text, solution):
        return _detailed_fallback(lead)

    return final_text


def _detailed_fallback(lead: dict) -> str:
    """Detailed fallback used when Ollama generation fails or is too short."""
    name = _lead_value(lead, "name", "there")
    company = _lead_value(lead, "company", "your business")
    solution = _lead_value(lead, "niche", "growth")
    industry = _lead_value(lead, "industry", "your industry")

    return _ascii_safe(
        f"Subject: Scaling {industry} growth with {solution}\n"
        f"Hi {name},\n\n"
        f"I came across {company} and wanted to reach out because teams in {industry} are seeing major shifts in how buyers discover and compare vendors.\n\n"
        f"Right now, the market is rewarding businesses that show clear expertise early in the buyer journey. Competitors that publish stronger proof, capture higher-intent traffic, and follow up faster are winning disproportionate share.\n\n"
        f"For many {industry} businesses, the bottleneck is not effort, but conversion quality: campaigns generate activity, but not enough qualified opportunities that move to revenue.\n\n"
        f"Our {solution} approach focuses on fixing that gap with tighter messaging, better targeting, and funnel improvements. Typical outcomes include higher lead-to-meeting rates and more predictable pipeline from the same marketing spend.\n\n"
        f"If useful, I can share a short 15-minute teardown tailored to {company} and outline where the quickest gains are likely.\n\n"
        "Best regards,"
    )


def _solution_alignment_ok(email_text: str, solution: str) -> bool:
    expected = (solution or "").strip().lower()
    if not expected:
        return True

    lines = email_text.splitlines()
    if not lines:
        return False

    subject = lines[0].lower()
    body = "\n".join(lines[1:]).lower()
    return expected in subject and expected in body


def _log_result(result: str, error: str) -> None:
    try:
        with open("ai_generation.log", "a", encoding="utf-8") as logf:
            if error:
                logf.write(f"[OLLAMA_ERROR] {error}\n")
            logf.write(result + "\n---\n")
    except Exception:
        pass


def generate_cold_email(lead: dict) -> str:
    """Generate a detailed cold email using Ollama with resilient fallback."""
    prompt = _build_prompt(lead)
    raw_result, error = _generate_with_ollama(prompt)
    result = _normalize_email(raw_result, lead) if raw_result else _detailed_fallback(lead)
    _log_result(result, error)
    return result
