# from fastapi import FastAPI, File, UploadFile
# from pydantic import BaseModel
# # from googletrans import Translator
# from gtts import gTTS
# from fastapi.responses import JSONResponse
# import os
# import shutil

# app = FastAPI()

# # Ensure the audio directory exists
# audio_folder = "audio_files"
# if not os.path.exists(audio_folder):
#     os.makedirs(audio_folder)

# # Class to handle the translation request
# class TranslationRequest(BaseModel):
#     text: str
#     source_lang: str
#     target_lang: str

# @app.post("/translate_audio")
# async def translate_audio(request: TranslationRequest):
#     try:
#         # Here, you would transcribe the audio file (e.g., using Google Cloud Speech-to-Text)
#         # For now, we'll simulate a translation of the transcribed text
#         transcription = request.text  # In this case, the frontend sends text as transcription

#         # Translate the transcription
#         translator = Translator()
#         translated = translator.translate(transcription, src=request.source_lang, dest=request.target_lang)
#         translated_text = translated.text

#         # Generate audio from the translated text
#         tts = gTTS(translated_text, lang=request.target_lang)
#         translated_audio_path = f"{audio_folder}/translated_audio.mp3"
#         tts.save(translated_audio_path)

#         # Return translated text and audio URL
#         audio_url = f"/static/{translated_audio_path.split('/')[-1]}"
#         return JSONResponse(content={"translated_text": translated_text, "audio_url": audio_url})

#     except Exception as e:
#         return JSONResponse(content={"message": f"Error: {str(e)}"}, status_code=500)

# # Serve static files (audio)
# from fastapi.staticfiles import StaticFiles
# app.mount("/static", StaticFiles(directory=audio_folder), name="static")


from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
import assemblyai as aai
# from elevenlabs.client import ElevenLabs
# from elevenlabs import stream
import uuid
import shutil
import os
import json
from dotenv import load_dotenv
from .utils import get_chatbot_response
from .translate import TranslateAgent
from fastapi.middleware.cors import CORSMiddleware
# from google.cloud import texttospeech
import io
import base64
import requests
load_dotenv()


app = FastAPI()


# languages_codes = {
#     "English": "en",
#     "Mandarin Chinese": "zh",
#     "Hindi": "hi",
#     "Spanish": "es",
#     "French": "fr",
#     "Standard Arabic": "ar",
#     "Bengali": "bn",
#     "Portuguese": "pt",
#     "Russian": "ru",
#     "Urdu": "ur"
# }

language_codes = json.load(open("/home/hammad/Project/translation_app/backend/languages.json"))

# Initialize FastAPI app
app = FastAPI()



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up API keys for AssemblyAI and ElevenLabs
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
# elevenlabs_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
GOOGLE_API_KEY = os.getenv("GOOGLE_CLOUD_API")  # Replace with your API key
translate_agent = TranslateAgent()

# Create directories for temporary audio storage
os.makedirs("audio", exist_ok=True)
os.makedirs("tts_audio", exist_ok=True)

# 🎤 Speech-to-Text using AssemblyAI (Now accepts a language parameter)
@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...), language: str = Form(...)):
    try:
        file_id = str(uuid.uuid4())
        file_path = f"audio/{file_id}.wav"

        # Save uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)

        language_code = language_codes.get(language, {}).get("assemblyai")

        # Upload file to AssemblyAI for transcription with specified language
        config = aai.TranscriptionConfig(language_code=language_code)

        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(file_path)

        # Cleanup: Delete file after transcription
        os.remove(file_path)

        return {"transcription": transcript.text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

# 🌍 Text Translation (Placeholder function - can integrate DeepL, Google Translate, etc.)
@app.post("/translate")
async def translate(text: str = Form(...), input_language: str = Form(...), target_language: str = Form(...)):
    try:
        # Use a translation API or AI model
        # translated_text = f"Translated [{text}] to {target_language}"  # Mock translation
        translated_text = translate_agent.get_response(text, input_language, target_language)
        translated_text = translated_text["translated_text"]
        return {"translated_text": translated_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")

# # 🔊 Text-to-Speech using ElevenLabs
# @app.post("/text-to-speech")
# async def text_to_speech(text: str = Form(...), language: str = Form(...)):
#     try:
#         file_id = str(uuid.uuid4())
#         file_path = f"tts_audio/{file_id}.wav"

#         # Generate speech from text
#         audio_stream = elevenlabs_client.generate(text=text, model="eleven_turbo_v2", stream=True)

#         # Save audio stream to file
#         with open(file_path, "wb") as audio_file:
#             for chunk in audio_stream:
#                 audio_file.write(chunk)

#         # Stream back audio response
#         def iterfile():
#             with open(file_path, "rb") as f:
#                 yield from f

#         response = StreamingResponse(iterfile(), media_type="audio/wav")
#         response.headers["Content-Disposition"] = f"attachment; filename={file_id}.wav"

#         return response

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Text-to-Speech failed: {str(e)}")



@app.post("/text-to-speech")
async def text_to_speech(text: str = Form(...), language: str = Form(...), audio_encoding: str = Form("MP3")):
    try:
        file_id = str(uuid.uuid4())
        file_path = f"tts_audio/{file_id}.{audio_encoding.lower()}"

        url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_API_KEY}"
        language_code = language_codes.get(language, {}).get("google_cloud")

        payload = {
            "input": {"text": text},
            "voice": {"languageCode": language_code, "name": f"{language_code}-Wavenet-D"},
            "audioConfig": {"audioEncoding": audio_encoding},
        }

        headers = {"Content-Type": "application/json"}

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            audio_content = response.json()["audioContent"]
            audio_bytes = base64.b64decode(audio_content)

            with open(file_path, "wb") as out_file:
                out_file.write(audio_bytes)

            async def iterfile():
                with open(file_path, "rb") as f:
                    while chunk := f.read(1024):
                        yield chunk

            response_stream = StreamingResponse(iterfile(), media_type=f"audio/{audio_encoding.lower()}")
            response_stream.headers["Content-Disposition"] = f"attachment; filename={file_id}.{audio_encoding.lower()}"

            return response_stream
        else:
            raise HTTPException(status_code=response.status_code, detail=f"Google Cloud API error: {response.text}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text-to-Speech failed: {str(e)}")

# ✅ Ready for deployment on Vercel, V0, or any cloud platform!
