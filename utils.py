
def get_chatbot_response(client,model_name,messages,temperature=0):
    input_messages = []
    for message in messages:
        input_messages.append({"role": message["role"], "content": message["content"]})

    response = client.chat.completions.create(
        model=model_name,
        messages=input_messages,
        temperature=temperature,
        top_p=0.8,
        max_tokens=2000,
    ).choices[0].message.content
    
    return response

def get_embedding(embedding_client,model_name,text_input):
    output = embedding_client.embeddings.create(input = text_input,model=model_name)
    
    embedings = []
    for embedding_object in output.data:
        embedings.append(embedding_object.embedding)

    return embedings

def double_check_json_output(client,model_name,json_string):
    prompt = f""" You will check this json string and correct any mistakes that will make it invalid. Then you will return the corrected json string. Nothing else. 
    If the Json is correct just return it.

    Do NOT return a single letter outside of the json string.

    {json_string}
    """

    messages = [{"role": "user", "content": prompt}]

    response = get_chatbot_response(client,model_name,messages)

    return response


def read_pdf(file_path):
    try:

        # Open the PDF file in binary mode
        with open(file_path, 'rb') as file:
            # Create a PDF reader object
            reader = PyPDF2.PdfReader(file)

            # Get the number of pages
            num_pages = len(reader.pages)
            content = ""
            # Loop through all the pages and extract text
            for page_num in range(num_pages):
                # Get the page object
                page = reader.pages[page_num]
                # Extract text from the page
                text = page.extract_text()
                text = text.replace("\n", " ")
                text = "\n".join(["Question" + paragraph for paragraph in text.split("Question")])
                content += text
            # content = content.replace("\n", " ")
            return content
    except:
        # Create a PDF reader object
        reader = PyPDF2.PdfReader(file_path)

        # Get the number of pages
        num_pages = len(reader.pages)
        content = ""
        # Loop through all the pages and extract text
        for page_num in range(num_pages):
            # Get the page object
            page = reader.pages[page_num]
            # Extract text from the page
            text = page.extract_text()
            text = text.replace("\n", " ")
            text = "\n".join(["Question" + paragraph for paragraph in text.split("Question")])
            content += text
        # content = content.replace("\n", " ")
        return content
        
def process_llm(key_text, student_text,total_marks,  prompt, client,   model  = "llama-3.1-8b-instant", temprature = 0.1):
    client = Groq()
    # Format the prompt with the context and the question
    prompt = ChatPromptTemplate.from_template(prompt)
    formatted_prompt = prompt.format(key_content=key_text, student_content=student_text, total_marks = total_marks)

    chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": formatted_prompt,
        }
    ],
    model = model,
    # model="llama-3.1-8b-instant",
    # model = "llama-3.1-70b-versatile",
    # model = "mixtral-8x7b-32768",
    temperature= temprature
    )
    response = chat_completion.choices[0].message.content
    try:
        response  = json.loads(response)
        return response
    except:
        print("Response is not json")
        return None


# Function to process PDFs
def process_pdfs(answer_key_pdf, student_zip,total_marks,  prompt, client,   model  = "llama-3.1-8b-instant", temprature = 0.1):
    # For simplicity, we will just list student PDF filenames and total marks.
    student_data = []

    
    key_text = read_pdf(answer_key_pdf)
    # print(key_text)

    # Extract student PDFs from the zip file
    with zipfile.ZipFile(student_zip, 'r') as zip_ref:
        zip_ref.extractall("student_pdfs")

        for pdf_file in os.listdir("pdfs"):
            if pdf_file.endswith(".pdf"):
                student_text = read_pdf(f"student_pdfs/pdfs/{pdf_file}")
                # print(pdf_file)
                # print(student_text)
                # student_data.append({"Student PDF": pdf_file, "Total Marks": total_marks})

                try:
                    json_response = process_llm(key_text, student_text,total_marks,  prompt, client,  model  = model, temprature = 0.1)
                    res = {
                        "file_name": pdf_file,
                        "Q1_marks": json_response["Q1"]["q1_assigned_marks"] ,
                        "Q2_marks": json_response["Q2"]["q2_assigned_marks"] ,
                        "Q3_marks": json_response["Q3"]["q3_assigned_marks"] ,
                        "total_marks_assigned" : json_response["overall_feedback"]["assigned_score"]
                    }
                    print(json_response)
                    student_data.append(res)
                except Exception as e:
                    print(e)
                
                # # Remove an empty directory
                # os.rmdir("/home/hammad/Project/auto_assignment_check/student_pdfs")
                # Remove the directory and all its contents
                # shutil.rmtree(directory)
                # Remove the directory and all its contents
                # directory = "/home/hammad/Project/auto_assignment_check/student_pdfs"
                # shutil.rmtree(directory)

                
        # Create a DataFrame
        df = pd.DataFrame(student_data)
        return df
