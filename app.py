import os
from flask import Flask, request, jsonify
from openai import OpenAI
from mindsdb_sdk.utils.mind import create_mind, DatabaseConfig
from config import api_key

app = Flask(__name__)

# Environment variable for the API key
api_key = os.getenv('apiKey')

base_url = 'https://llm.mdb.ai/'
client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

mind_name = '_yodb_mind'

# Define the database configuration
pg_config = DatabaseConfig(
    description='Demo data',
    type='postgres',
    connection_args={
        'user': 'demo_user',
        'password': 'demo_password',
        'host': 'samples.mindsdb.com',
        'port': '5432',
        'database': 'demo',
        'schema': 'demo_data'
    },
    tables=['house_sales']
)

# Initialize the mind
try:
    # Create or verify the mind
    existing_minds = client.beta.minds.list()  # Use the updated method to list minds
    mind_exists = any(mind.name == mind_name for mind in existing_minds.data)

    if not mind_exists:
        mind = create_mind(
            name=mind_name,
            base_url=base_url,
            api_key=api_key,
            data_source_configs=[pg_config]
        )
        print(f"Created mind: {mind.name}")
    else:
        print(f"Mind {mind_name} already exists. Skipping creation.")
except Exception as e:
    print(f"Error during mind initialization: {e}")

# Global thread to allow continuous conversation
current_thread = None

@app.route('/chatbot', methods=['POST'])
def chatbot():
    global current_thread
    
    user_input = request.json.get('message')
    
    if not current_thread:
        current_thread = client.beta.threads.create()

    prompt_template = 'You are Deadpool, give comments on the user input like a therapist Deadpool in his sarcastic and psychotic way: {input}'
    formatted_input = prompt_template.format(input=user_input)

    message = client.beta.threads.messages.create(
        thread_id=current_thread.id,
        role="user",
        content=formatted_input
    )

    run = client.beta.threads.runs.create_and_poll(
        thread_id=current_thread.id,
        assistant_id=mind_name
    )

    if run.status == 'completed':
        messages = client.beta.threads.messages.list(thread_id=current_thread.id)
        assistant_response = ""
        for message in messages.data:
            if message.role == "assistant":
                assistant_response = message.content[0].text.value
        return jsonify({'response': assistant_response})
    else:
        return jsonify({'response': "Assistant did not complete the request.", 'status': run.status}), 500

@app.route('/end_session', methods=['POST'])
def end_session():
    global current_thread
    if current_thread:
        client.beta.threads.delete(current_thread.id)
        current_thread = None
        return jsonify({'response': "Session ended."})
    return jsonify({'response': "No session to end."}), 400

if __name__ == '__main__':
    app.run(debug=True)
