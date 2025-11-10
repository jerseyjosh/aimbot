from pydantic import BaseModel, computed_field

from aimbot.models.news import NewsStory

class RadioNewsData(BaseModel):
    speaker_id: str
    stories: list[NewsStory]
    weather: str
    script: str = ""

    @computed_field
    @property
    def generated_script(self) -> str:
        """Generate a default radio news script from the data"""
        script = f"Bailiwick Radio News, I'm {self.speaker_id}. Here are today's top stories.\n\n"
        # stories
        for i, story in enumerate(self.stories):
            if i == 1:
                script += "In other news, "
            if i == 2:
                script += "Meanwhile in Guernsey, "
            if i == 3:
                script += "Also in Guernsey, "
            first_sentences = '. '.join(story.text.split(".")[:2])
            script += f"{first_sentences}.\n\n"
        # strapline
        script += "For more on all these stories, visit Bailiwick Express dot com.\n\n"
        # weather
        script += f"Now for the weather. {self.weather}\n\n"
        # outro
        script += "You're up to date with Bailiwick Radio News."
        return script