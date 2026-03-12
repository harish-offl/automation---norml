import subprocess
from ai_engine import generate_cold_email


def test_generate_cold_email_logs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    class Dummy:
        stdout = (
            "Subject: Better SEO Services lead flow for construction brands\n"
            "Hi Ram,\n\n"
            "Construction buyers now shortlist vendors online before speaking with sales teams. "
            "The market is rewarding firms with strong proof and clear service positioning.\n\n"
            "Most teams lose momentum between clicks and qualified conversations because pages "
            "and follow-up workflows are disconnected.\n\n"
            "We fix this with SEO Services by tightening offer messaging, improving conversion paths, and building "
            "lead scoring follow-ups that prioritize high-intent prospects.\n\n"
            "Teams usually see stronger lead quality and better meeting rates within a few weeks.\n\n"
            "If helpful, I can share a quick 15-minute growth teardown for your funnel."
        )
        stderr = ""

    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: Dummy())

    lead = {"name": "Ram", "niche": "SEO Services", "industry": "Construction", "company": "Ram Constructions"}
    result = generate_cold_email(lead)
    assert "Subject" in result
    assert "Hi Ram" in result
    assert "SEO Services" in result

    content = (tmp_path / "ai_generation.log").read_text(encoding="utf-8")
    assert "Subject: Better SEO Services lead flow for construction brands" in content


def test_generate_cold_email_uses_detailed_fallback_when_ollama_fails(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=args[0], stderr="command failed")

    monkeypatch.setattr("subprocess.run", fail)

    lead = {"name": "Annamalai", "niche": "App Development", "industry": "IT Services", "company": "TechNova"}
    result = generate_cold_email(lead)

    assert result.startswith("Subject:")
    assert "market is rewarding" in result
    assert "We thought you might be interested in ..." not in result
