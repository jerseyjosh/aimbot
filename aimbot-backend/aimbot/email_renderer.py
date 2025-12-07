from typing import Union, Optional
from pathlib import Path
import re

from pydantic import BaseModel

import jinja2

class EmailRenderer:
    def __init__(self, template_name: str):
        self.template_name = template_name
        # Get the templates directory relative to this file
        templates_dir = Path(__file__).parent / "templates"
        self.template_loader = jinja2.FileSystemLoader(templates_dir)
        self.template_env = jinja2.Environment(loader=self.template_loader)
        self.template_env.filters["first_sentence"] = self.first_sentence
        self.template = self.template_env.get_template(self.template_name)

    def render(self, data: BaseModel) -> str:
        """Render the email template with the current data."""
        return self.template.render(dict(data))

    @staticmethod
    def first_sentence(text: Optional[str]) -> str:
        """Extract the first sentence from a string, handling decimal numbers properly"""
        if not text:
            return ""
        
        # Look for period followed by:
        # - whitespace (including zero-width chars) and capital letter
        # - directly by capital letter (no space)
        # - end of string
        # But not period between digits (decimal numbers)
        sentence_end_pattern = r'\.(?=[\s\u200b]*[A-Z]|$)(?!\d)'
        
        match = re.search(sentence_end_pattern, text)
        if match:
            return text[:match.end()]
        else:
            # No sentence ending found, return the whole text
            return text