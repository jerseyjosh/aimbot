import os
from dotenv import load_dotenv, find_dotenv

from elevenlabs import ElevenLabs as APIClient
from elevenlabs import save, VoiceSettings

load_dotenv(find_dotenv())

class ElevenLabs:

    MODEL = "eleven_multilingual_v2"
    SETTINGS = VoiceSettings(stability=0.75, similarity_boost=0.75, use_speaker_boost=False)

    def __init__(self, api_key: str = os.getenv("ELEVENLABS_API_KEY")):
        self.client = APIClient(api_key=api_key)
        self.voice_to_id = None

    def get_voice_to_id(self, use_cache: bool = True) -> dict[str, str]:
        if use_cache and self.voice_to_id is not None:
            return self.voice_to_id
        self.voice_to_id = {v.name: v.voice_id for v in self.get_custom_voices()}
        return self.voice_to_id

    def get_custom_voices(self):
        voices = self.client.voices.get_all().voices
        return [v for v in voices if v.name.lower().startswith('aim')]
    
    def generate(self, text: str, voice: str) -> bytes:
        voice_to_id = self.get_voice_to_id()
        if voice not in voice_to_id:
            raise ValueError(f"Voice {voice} not found among custom voices: {list(voice_to_id.keys())}")
        audio_generator = self.client.text_to_speech.convert(voice_id=voice_to_id[voice], text=text, model_id=self.MODEL, voice_settings=self.SETTINGS)
        # Collect all audio chunks from the generator
        audio_bytes = b''.join(audio_generator)
        return audio_bytes


if __name__ == "__main__":
    client = ElevenLabs()
    voice_to_id = client.get_voice_to_id() 
    breakpoint()