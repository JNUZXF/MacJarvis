# File: backend/app/services/memory_extractor.py
# Purpose: Extract memories from conversations using LLM
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MemoryExtractor:
    """Extract structured memories from conversation messages using LLM"""

    EXTRACTION_PROMPT = """You are a memory extraction system. Analyze the conversation and extract structured memories about the user.

Extract the following types of memories:

1. **Preferences** - User's stated preferences
   - Examples: "I prefer concise responses", "I'm vegetarian", "I like dark mode"

2. **Facts** - Objective information about the user
   - Examples: Name, job, location, family members, education

3. **Tasks** - Work items, TODOs, projects, goals
   - Examples: "Working on a Python project", "Need to fix the login bug"

4. **Relations** - Relationships between entities
   - Examples: "Alice is my manager", "Project X belongs to Team Y"

Respond with a JSON object in this exact format:
{
  "preferences": [
    {
      "category": "communication",
      "key": "response_style",
      "value": "concise and direct",
      "confidence": 8,
      "source": "explicit"
    }
  ],
  "facts": [
    {
      "type": "personal",
      "subject": "name",
      "value": "John Doe",
      "confidence": 10,
      "source": "direct_statement"
    }
  ],
  "tasks": [
    {
      "type": "project",
      "title": "Build user authentication",
      "description": "Implement JWT-based auth system",
      "status": "active",
      "priority": "high"
    }
  ],
  "relations": [
    {
      "subject": "Alice",
      "subject_type": "person",
      "relation": "is_manager_of",
      "object": "me",
      "object_type": "person",
      "confidence": 9
    }
  ]
}

Rules:
- Only extract clear, explicit information
- Don't make assumptions or inferences unless confidence is high
- Confidence scale: 1-10 (1=very uncertain, 10=absolutely certain)
- If no memories found, return empty arrays
- Use "explicit" source for directly stated info, "inferred" for contextual info

Conversation to analyze:
"""

    def __init__(self, llm_service):
        """
        Initialize memory extractor

        Args:
            llm_service: LLM service instance for making API calls
        """
        self.llm_service = llm_service

    async def extract_from_messages(
        self,
        messages: List[Dict[str, Any]],
        user_id: str,
        session_id: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract memories from a list of conversation messages

        Args:
            messages: List of message dicts with 'role' and 'content'
            user_id: User ID for context
            session_id: Optional session ID for context

        Returns:
            Dict with keys: preferences, facts, tasks, relations
        """
        try:
            # Format conversation for analysis
            conversation_text = self._format_conversation(messages)

            # Prepare LLM messages
            llm_messages = [
                {
                    "role": "system",
                    "content": self.EXTRACTION_PROMPT
                },
                {
                    "role": "user",
                    "content": conversation_text
                }
            ]

            # Call LLM to extract memories
            response = await self.llm_service.chat_completion(
                messages=llm_messages,
                model="gpt-4o-mini",  # Use efficient model for extraction
                temperature=0.3,  # Lower temperature for more consistent extraction
                max_tokens=2000
            )

            # Parse response
            extracted = self._parse_extraction_response(response)

            # Add metadata
            extracted = self._add_metadata(extracted, user_id, session_id)

            logger.info(
                f"Extracted memories for user {user_id}: "
                f"{len(extracted['preferences'])} preferences, "
                f"{len(extracted['facts'])} facts, "
                f"{len(extracted['tasks'])} tasks, "
                f"{len(extracted['relations'])} relations"
            )

            return extracted

        except Exception as e:
            logger.error(f"Error extracting memories: {e}", exc_info=True)
            return {
                "preferences": [],
                "facts": [],
                "tasks": [],
                "relations": []
            }

    def _format_conversation(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages into readable conversation text"""
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # Skip system messages and empty messages
            if role == "system" or not content:
                continue

            # Format as "User: ..." or "Assistant: ..."
            role_label = "User" if role == "user" else "Assistant"
            lines.append(f"{role_label}: {content}")

        return "\n\n".join(lines)

    def _parse_extraction_response(self, response: str) -> Dict[str, List[Dict]]:
        """Parse LLM response into structured memory data"""
        try:
            # Try to find JSON in response
            response = response.strip()

            # Handle markdown code blocks
            if response.startswith("```"):
                # Extract content between ```json and ```
                start = response.find("```json")
                if start == -1:
                    start = response.find("```")
                end = response.rfind("```")
                if start != -1 and end != -1 and end > start:
                    response = response[start:end]
                    response = response.replace("```json", "").replace("```", "").strip()

            # Parse JSON
            data = json.loads(response)

            # Validate structure
            return {
                "preferences": data.get("preferences", []),
                "facts": data.get("facts", []),
                "tasks": data.get("tasks", []),
                "relations": data.get("relations", [])
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse extraction response as JSON: {e}")
            logger.debug(f"Response was: {response}")
            return {
                "preferences": [],
                "facts": [],
                "tasks": [],
                "relations": []
            }

    def _add_metadata(
        self,
        extracted: Dict[str, List[Dict]],
        user_id: str,
        session_id: Optional[str]
    ) -> Dict[str, List[Dict]]:
        """Add user_id and session_id to all extracted memories"""
        timestamp = datetime.utcnow().isoformat()

        for pref in extracted["preferences"]:
            pref["user_id"] = user_id
            pref["extracted_at"] = timestamp
            if session_id:
                pref["session_id"] = session_id

        for fact in extracted["facts"]:
            fact["user_id"] = user_id
            fact["extracted_at"] = timestamp
            if session_id:
                fact["session_id"] = session_id

        for task in extracted["tasks"]:
            task["user_id"] = user_id
            task["extracted_at"] = timestamp
            if session_id:
                task["session_id"] = session_id

        for relation in extracted["relations"]:
            relation["user_id"] = user_id
            relation["extracted_at"] = timestamp
            if session_id:
                relation["session_id"] = session_id

        return extracted

    async def extract_from_single_message(
        self,
        user_message: str,
        assistant_response: str,
        user_id: str,
        session_id: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract memories from a single message exchange

        Args:
            user_message: User's message
            assistant_response: Assistant's response
            user_id: User ID
            session_id: Optional session ID

        Returns:
            Extracted memories
        """
        messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_response}
        ]
        return await self.extract_from_messages(messages, user_id, session_id)
