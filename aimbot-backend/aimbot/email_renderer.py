from typing import Union, Optional
from pathlib import Path

from pydantic import BaseModel

import jinja2

class EmailRenderer:
    def __init__(self, template_name: str):
        self.template_name = template_name
        # Get the templates directory relative to this file
        templates_dir = Path(__file__).parent.parent / "templates"
        self.template_loader = jinja2.FileSystemLoader(templates_dir)
        self.template_env = jinja2.Environment(loader=self.template_loader)
        self.template_env.filters["first_sentence"] = self.first_sentence
        self.template = self.template_env.get_template(self.template_name)

    def render(self, data: BaseModel) -> str:
        """Render the email template with the current data."""
        return self.template.render(dict(data))

    @staticmethod
    def first_sentence(text: Optional[str]) -> str:
        """Extract the first sentence from a string, for passing to Jinja"""
        if not text:
            return ""
        first = text.split(".")[0]
        return first + "." if first and not first.endswith(".") else first
    