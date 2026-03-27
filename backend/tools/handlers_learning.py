"""Learning tool handlers — code tutor, YouTube transcript."""
import re


# ── Code Tutor ──────────────────────────────────────────────────────────────

async def _tutor_topics(args: dict) -> dict:
    from tools.code_tutor import get_topics
    return {"topics": get_topics()}

async def _tutor_challenge(args: dict) -> dict:
    from tools.code_tutor import get_challenge
    topic = args.get("topic", "python_basics")
    difficulty = args.get("difficulty", "")
    challenge_id = args.get("challenge_id", "")
    challenge = get_challenge(topic, difficulty, challenge_id)
    if not challenge:
        return {"error": f"No challenge found for topic: {topic}"}
    return challenge

async def _tutor_validate(args: dict) -> dict:
    from tools.code_tutor import validate_solution, save_progress
    challenge_id = args.get("challenge_id", "")
    code = args.get("code", "")
    if not challenge_id or not code:
        return {"error": "challenge_id and code are required"}
    result = validate_solution(challenge_id, code)
    # Save progress
    topic = challenge_id.split(":")[0] if ":" in challenge_id else ""
    progress = save_progress(topic, challenge_id, result.get("passed", False))
    result["progress"] = progress
    return result

async def _tutor_validate_dynamic(args: dict) -> dict:
    """Validate code against AI-generated test cases (for dynamic challenges)."""
    from tools.code_tutor import validate_dynamic_challenge
    code = args.get("code", "")
    test_code = args.get("test_code", "")
    language = args.get("language", "python")
    if not code or not test_code:
        return {"error": "code and test_code are required"}
    return validate_dynamic_challenge(code, test_code, language)

async def _tutor_progress(args: dict) -> dict:
    from tools.code_tutor import get_progress
    return get_progress()


# ── YouTube Transcript ──────────────────────────────────────────────────────

async def _youtube_transcript(args: dict) -> dict:
    """Get transcript/captions from a YouTube video."""
    from youtube_transcript_api import YouTubeTranscriptApi

    url = args.get("url", "")
    # Extract video ID from various URL formats
    video_id = ""
    patterns = [
        r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$',
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            video_id = m.group(1)
            break

    if not video_id:
        return {"error": f"Could not extract video ID from: {url}"}

    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id)

        # Combine all text segments
        full_text = ""
        for segment in transcript.snippets:
            full_text += segment.text + " "

        full_text = full_text.strip()

        # Truncate if very long
        if len(full_text) > 15000:
            full_text = full_text[:15000] + "\n\n...(truncated)"

        return {
            "video_id": video_id,
            "transcript": full_text,
            "word_count": len(full_text.split()),
            "url": f"https://youtube.com/watch?v={video_id}",
        }
    except Exception as e:
        return {"error": f"Could not get transcript: {str(e)}. The video may not have captions available."}
