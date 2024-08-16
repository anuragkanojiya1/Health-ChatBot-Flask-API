import os
from flask import Flask, request, jsonify
from openai import OpenAI
from mindsdb_sdk import Client, DatabaseConfig, create_mind

app = Flask(__name__)

# Load environment variable
api_key = os.getenv('apiKey')

# MindsDB base URL
base_url = 'https://llm.mdb.ai/'

# Initialize MindsDB client
client = Client(api_key=api_key, base_url=base_url)

mind_name = '_yodb_mind'

# Initialize the mind
try:
    pg_config = DatabaseConfig(
        description='Whales',
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

    # Create or check if mind exists
    existing_minds = client.minds.list()
    mind_exists = any(mind.name == mind_name for mind in existing_minds)

    if not mind_exists:
        mind = create_mind(
            name=mind_name,
            base_url=base_url,
            api_key=api_key,
            data_source_configs=[pg_config]
        )
        print(f"{mind.name} was created successfully. You can now use this Mind using the OpenAI-compatible API.")
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
        current_thread = client.threads.create()

    prompt_template = 'You are Deadpool, give comments on the user input like a therapist Deadpool in his sarcastic and psychotic way: {input}'
    formatted_input = prompt_template.format(input=user_input)

    message = client.threads.messages.create(
        thread_id=current_thread.id,
        role="user",
        content=formatted_input
    )

    run = client.threads.runs.create_and_poll(
        thread_id=current_thread.id,
        assistant_id=mind_name
    )

    if run.status == 'completed':
        messages = client.threads.messages.list(thread_id=current_thread.id)
        assistant_response = ""
        for message in messages:
            if message.role == "assistant":
                assistant_response = message.content
        return jsonify({'response': assistant_response})
    else:
        return jsonify({'response': "Assistant did not complete the request.", 'status': run.status}), 500

@app.route('/end_session', methods=['POST'])
def end_session():
    global current_thread
    if current_thread:
        client.threads.delete(current_thread.id)
        current_thread = None
        return jsonify({'response': "Session ended."})
    return jsonify({'response': "No session to end."}), 400

if __name__ == '__main__':
    app.run(debug=True)
