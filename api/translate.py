from dotenv import load_dotenv
import os
import json
from .utils import get_chatbot_response
from openai import OpenAI
import re
load_dotenv()

class TranslateAgent():
    def __init__(self):

        self.client = OpenAI(
            api_key=os.getenv("GROQ_TOKEN"),
            base_url=os.getenv("GROQ_CHATBOT_URL"),
        )
        self.model_name = os.getenv("MODEL_NAME")
    
    def get_response(self, text, input_langauge, target_language):

        system_prompt = """
            **Role**: You are a medical translation AI that returns responses in JSON format.

            **Instructions**:
            1. Accurately translate healthcare text between specified languages
            2. Maintain medical terminology. Do not simplify or generalize medical terms.
            3. ALWAYS return output in this exact JSON structure:
            {
                "translated_text": "[translated_text].,
                "target_language": "[target_language]"
            }

            **Example Input**:
            Text: "Dolor de cabeza severo"
            Input Language: Spanish
            Target Language: English

            **Example Output**:
            {
                "translated_text": "Severe headache.",
                "target_language": "English"
            }

            **Start all responses with '{' and end with '}'**
            """

        user_prompt = f"""
        Text: {text}
        Input Language:{input_langauge}
        Target Language: {target_language}
        """
        input_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
            ]

        output =get_chatbot_response(self.client,self.model_name,input_messages)
        out = self.postprocess(output)
        
        return out
        # return output

    def postprocess(self,output):
        # Remove the <think> section
        cleaned_text = re.sub(r"<think>.*?</think>", "", output, flags=re.DOTALL)

        # Remove triple backticks and "json" label
        cleaned_text = re.sub(r"```json\s*", "", cleaned_text)
        cleaned_text = re.sub(r"```", "", cleaned_text)

        # Extract JSON part
        json_match = re.search(r"(\{.*\})", cleaned_text, flags=re.DOTALL)
        if json_match:
            json_text = json_match.group(1).strip()
            
            try:
                # Load as JSON
                out = json.loads(json_text)

                # # Pretty print the JSON output
                # out = json.dumps(json_data, indent=4)
            except json.JSONDecodeError as e:
                print("Error decoding JSON:", e)

        return out
        


    