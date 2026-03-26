# ── Tool Definitions (sent to Ollama) ───────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_code",
            "description": "Execute code and return output. Use for calculations, data processing, scripts, or demonstrations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Code to execute"},
                    "language": {"type": "string", "enum": ["python", "javascript", "bash"], "default": "python", "description": "Programming language"},
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information, news, facts, or anything you don't know.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Fetch and read the content of a webpage URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_datetime",
            "description": "Get the current date and time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string", "description": "Timezone name (optional)", "default": "local"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name or location"},
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a mathematical expression. Supports all Python math functions (sin, cos, sqrt, log, pi, e, etc).",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Math expression to evaluate, e.g. 'sqrt(144) + pi'"},
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_search",
            "description": "Search Gmail emails. Use Gmail search syntax like 'from:user@example.com', 'subject:hello', 'is:unread', 'newer_than:2d'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Gmail search query"},
                    "max_results": {"type": "integer", "description": "Max emails to return", "default": 10},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_read",
            "description": "Read the full content of a specific email by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Email message ID"},
                },
                "required": ["id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_send",
            "description": "Send an email or reply to an existing email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email body text"},
                    "reply_to_id": {"type": "string", "description": "Message ID to reply to (optional)"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calendar_list",
            "description": "List upcoming Google Calendar events.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_ahead": {"type": "integer", "description": "Number of days to look ahead", "default": 7},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calendar_create",
            "description": "Create a new Google Calendar event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Event title"},
                    "start_time": {"type": "string", "description": "Start time in ISO 8601 format (e.g. 2026-03-25T10:00:00)"},
                    "end_time": {"type": "string", "description": "End time in ISO 8601 format"},
                    "description": {"type": "string", "description": "Event description"},
                    "location": {"type": "string", "description": "Event location"},
                    "timezone": {"type": "string", "description": "Timezone", "default": "America/New_York"},
                    "attendees": {"type": "array", "items": {"type": "string"}, "description": "List of attendee email addresses"},
                },
                "required": ["summary", "start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_artifact",
            "description": "Create a rich artifact (code file, document, HTML page, SVG, diagram) displayed in a side panel for the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Unique artifact ID"},
                    "type": {"type": "string", "enum": ["code", "document", "html", "svg", "react", "mermaid"]},
                    "title": {"type": "string", "description": "Artifact title"},
                    "content": {"type": "string", "description": "Artifact content"},
                    "language": {"type": "string", "description": "Programming language (for code type)"},
                },
                "required": ["id", "type", "title", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "Generate an image from a text description using AI (Gemini). Returns the file path of the generated image.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Detailed description of the image to generate"},
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_image",
            "description": "Edit an existing image with AI. Provide the file path and describe the changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {"type": "string", "description": "Full file path to the image to edit"},
                    "prompt": {"type": "string", "description": "Description of changes to make to the image"},
                },
                "required": ["image_path", "prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tutor_topics",
            "description": "List available coding tutorial topics and challenge counts.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tutor_challenge",
            "description": "Get a coding challenge for the user to solve. Returns the problem description, difficulty, and language.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Topic ID: python_basics, oop_basics, data_structures, javascript_basics, swift_basics"},
                    "difficulty": {"type": "string", "enum": ["beginner", "intermediate", "advanced"], "description": "Difficulty level"},
                    "challenge_id": {"type": "string", "description": "Specific challenge ID (optional)"},
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tutor_validate",
            "description": "Validate the user's code solution against the challenge's test cases. Runs the code and checks if all tests pass.",
            "parameters": {
                "type": "object",
                "properties": {
                    "challenge_id": {"type": "string", "description": "The challenge ID to validate against"},
                    "code": {"type": "string", "description": "The user's complete code solution"},
                },
                "required": ["challenge_id", "code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tutor_validate_dynamic",
            "description": "Validate user code against custom test cases you generate. Use this for AI-generated challenges when built-in challenges are exhausted.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "The user's code solution"},
                    "test_code": {"type": "string", "description": "Test code with assertions that prints 'All tests passed!' on success"},
                    "language": {"type": "string", "enum": ["python", "javascript"], "default": "python"},
                },
                "required": ["code", "test_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tutor_progress",
            "description": "Show the user's coding tutorial progress \u2014 completed challenges, total available, and percentage.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "codebase_tree",
            "description": "View the file and directory structure of a local project. Use this to understand a project's layout before reading specific files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Full path to the project directory, e.g. ~/WANDERLINK or ~/claude-ui"},
                    "max_depth": {"type": "integer", "description": "How deep to scan (default 3)", "default": 3},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "codebase_read",
            "description": "Read the contents of a specific file from a local project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Full path to the file to read, e.g. ~/WANDERLINK/Wanderlink/Services/WeatherService.swift"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "codebase_search",
            "description": "Search for text/code across all files in a local project directory. Returns matching lines with file paths and line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Full path to the project directory to search"},
                    "query": {"type": "string", "description": "Text to search for (case-insensitive)"},
                    "max_results": {"type": "integer", "description": "Max results to return", "default": 20},
                },
                "required": ["path", "query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_transcript",
            "description": "Get the transcript/captions from a YouTube video. Use this to summarize, analyze, or answer questions about YouTube videos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "YouTube video URL or video ID"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_note",
            "description": "Save a note or memory that persists across conversations. Also saves to Google Drive. Use this when the user asks you to remember something.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Note title"},
                    "content": {"type": "string", "description": "Note content (markdown supported)"},
                    "category": {"type": "string", "description": "Category (general, todo, reminder, preference)", "default": "general"},
                    "project": {"type": "string", "description": "Project name for organizing (e.g. 'GigLedger', 'WanderLink'). Creates a subfolder."},
                },
                "required": ["title", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_note",
            "description": "Read the full content of a saved note. Use list_notes first to find the filename.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "The note filename (e.g. 'GigLedger Project Overview.md')"},
                },
                "required": ["filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_note",
            "description": "Append new content to an existing note without losing existing data. Use list_notes first to find the filename.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "The note filename (e.g. 'GigLedger Project Overview.md')"},
                    "content": {"type": "string", "description": "New content to append to the note"},
                },
                "required": ["filename", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_notes",
            "description": "List and search saved notes/memories from previous conversations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional search query to filter notes"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "drive_list_files",
            "description": "List recent files in Google Drive, optionally filtered by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional filename search query"},
                    "max_results": {"type": "integer", "description": "Max files to return", "default": 15},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "drive_search",
            "description": "Search Google Drive files by content (full-text search).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query to find in file contents"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "drive_read_doc",
            "description": "Read the text content of a Google Doc by its document ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string", "description": "Google Doc document ID"},
                },
                "required": ["document_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "drive_create_doc",
            "description": "Create a new Google Doc with a title and content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Document title"},
                    "content": {"type": "string", "description": "Document text content"},
                },
                "required": ["title", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "security_camera",
            "description": "View the security camera feed. Captures a live snapshot from a security camera and analyzes it with AI vision to describe what is visible (people, vehicles, animals, packages, etc).",
            "parameters": {
                "type": "object",
                "properties": {
                    "camera": {"type": "string", "description": "Camera name (default: front_door)", "default": "front_door"},
                    "question": {"type": "string", "description": "Specific question about what you see (optional)"},
                },
            },
        },
    },
]
