"""LLM-based party member extractor for evaluation"""

import json
import logging
import re
from html.parser import HTMLParser
from typing import Any

logger = logging.getLogger(__name__)


class PartyMemberExtractor:
    """Extract party member information from HTML using LLM"""

    def __init__(self, llm_service: Any):
        """Initialize extractor with LLM service

        Args:
            llm_service: LLM service instance for text generation
        """
        self.llm_service = llm_service

    def extract_from_html(
        self, html_content: str, party_name: str
    ) -> list[dict[str, Any]]:
        """Extract party members from HTML content

        Args:
            html_content: HTML content containing member information
            party_name: Name of the political party

        Returns:
            List of extracted member dictionaries
        """
        try:
            # Create prompt for LLM
            prompt = f"""以下のHTMLから政党メンバーの情報を抽出してください。

政党名: {party_name}
HTML:
{html_content}

各メンバーについて以下の情報を抽出してください:
- name: 氏名（必須）
- position: 役職（あれば）
- district: 選挙区（あれば）
- email: メールアドレス（あれば）
- website: ウェブサイト（あれば）

JSON形式で、以下のような構造で返してください:
{{"members": [{{"name": "山田太郎", "position": "代表",
"district": "東京1区"}}, ...]}}"""

            # Call LLM service directly
            messages = [{"role": "user", "content": prompt}]
            response = self.llm_service.invoke_llm(messages)

            # Parse JSON response
            try:
                # Extract JSON from response
                json_match = re.search(r"\{.*\}", response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return result.get("members", [])
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")

            # Fallback: Try simple extraction
            members = []

            # Simple pattern matching for common formats
            # Pattern 1: <div class='member'>Name Position District</div>

            class MemberParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.members = []
                    self.current_text = []
                    self.in_member = False

                def handle_starttag(
                    self, tag: str, attrs: list[tuple[str, str | None]]
                ) -> None:
                    attrs_dict = dict(attrs)
                    class_attr = attrs_dict.get("class")
                    if class_attr and "member" in class_attr:
                        self.in_member = True
                        self.current_text = []

                def handle_data(self, data: str) -> None:
                    if self.in_member:
                        self.current_text.append(data.strip())

                def handle_endtag(self, tag: str) -> None:
                    if self.in_member:
                        self.in_member = False
                        text = " ".join(self.current_text)
                        if text:
                            # Parse text like "山田太郎 代表 東京1区"
                            parts = text.split()
                            if parts:
                                member = {"name": parts[0]}
                                if len(parts) > 1:
                                    member["position"] = parts[1]
                                if len(parts) > 2:
                                    member["district"] = parts[2]
                                self.members.append(member)

            parser = MemberParser()
            parser.feed(html_content)

            if parser.members:
                return parser.members

            # Pattern 2: List items
            list_pattern = r"<li>([^<]+)</li>"
            list_matches = re.findall(list_pattern, html_content)
            for match in list_matches:
                # Parse text like "佐藤次郎 - 幹事長 - 大阪1区 - sato@example.com"
                parts = [p.strip() for p in match.split(" - ")]
                if parts:
                    member = {"name": parts[0]}
                    if len(parts) > 1:
                        member["position"] = parts[1]
                    if len(parts) > 2:
                        member["district"] = parts[2]
                    if len(parts) > 3 and "@" in parts[3]:
                        member["email"] = parts[3]
                    members.append(member)

            return members

        except Exception as e:
            logger.error(f"Error extracting party members: {e}")
            return []
