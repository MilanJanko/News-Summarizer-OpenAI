import openai
from dotenv import find_dotenv, load_dotenv
import os
import time, logging
from datetime import datetime
import requests
import json
import streamlit as st

load_dotenv()

client = openai.OpenAI(api_key=os.environ.get('OPENAI_API_KEY'),
    organization="org-khIrQu0W6wbUnghDbHaxKxMP",
    base_url="https://api.openai.com/v1/",
    project="proj_4LCvgSJCJBLLMnEqpdhqGUWk",
    timeout=5)

model = "gpt-4o-mini"
news_api_key = os.environ.get("NEWS_API_KEY")

def get_news(topic):
    news_url = f"https://newsapi.org/v2/everything?q={topic}&apiKey={news_api_key}&pageSize=5"

    try:
        response = requests.get(news_url)
        if response.status_code == 200:
            news = json.dumps(response.json(), indent=4)
            news_json = json.loads(news)

            data = news_json
        # Check API request field in news api

            status = data['status']
            total_results = data['totalResults']
            articles = data['articles']
            news_final = []

            for article in articles:
                name = article['source']['name']
                author = article['author']
                title = article['title']
                description = article['description']
                url = article['url']
                content = article['content']
                title_description = f"""
                   Title: {title}, 
                   Author: {author},
                   Source: {name},
                   Description: {description},
                   URL: {url}
            
                """
                news_final.append(title_description)
            return news_final
        else:
            return []
            
    except requests.exceptions.RequestException as e:
        print("Error occured during API call", e)

class AssistantManager():
    assistant_id = "asst_F7ItGgTJS2IxUq6x6Hkfju0s"
    thread_id = "thread_SyQboiBBnZk5sNynOsFR9Kv3"

    def __init__(self, model: str = model):
        self.client = client
        self.model = model
        self.assistant = None
        self.thread = None
        self.run = None
        self.summary = None

        if AssistantManager.assistant_id:
            self.assistant_id = self.client.beta.assistants.retrieve(assistant_id=AssistantManager.assistant_id)

        if AssistantManager.thread_id:
            self.thread_id = self.client.beta.threads.retrieve(thread_id=AssistantManager.thread_id)    

    def create_assistant(self, name, instructions, tools):
        if not self.assistant:
            assistant_created = self.client.beta.assistants.create(model=self.model, name=name, instructions= instructions, tools=tools)
            AssistantManager.assistant_id= assistant_created.id
            self.assistant = assistant_created
            print(f"AssisID::: {self.assistant.id}")

    def create_thread(self):
        if not self.thread:
            thread_created = self.client.beta.threads.create()
            AssistantManager.thread_id = thread_created.id
            self.thread = thread_created
            print(f"ThreadID:::: {self.thread.id}")

    def add_message_to_thread(self, role, content):
        if self.thread:
            self.client.beta.threads.messages.create(thread_id=self.thread.id, content=content, role=role)

    def run_assistant(self, instructions):
        if self.assistant and self.thread:
            self.run = self.client.beta.threads.runs.create(thread_id=self.thread.id, 
                        assistant_id=self.assistant.id, instructions=instructions)

    def process_message(self):
        if self.thread:
            summary = []
            messages = self.client.beta.threads.messages.list(thread_id=self.thread.id)

            last_message = messages.data[0]
            response = last_message.content[0].text.value
            role = last_message.role
            summary.append(response)
            self.summary = "\n".join(summary)
            print(f"SUMMARY ---->{role.capitalize()}: {response}")

    def call_required_functions(self, required_actions):
        if not self.run:
            return
        tool_outputs = []

        for action in required_actions["tool_calls"]:
            func_name = action["function"]["name"]
            arguments = json.loads(action["function"]["arguments"])

            if func_name == "get_news":
                output = get_news(topic=arguments["topic"])
                print(f"STUFFFFF;;;;{output}")
                final_str = ""
                for item in output:
                    final_str += "".join(item)

                tool_outputs.append({"tool_call_id": action["id"], "output": final_str})
            else:
                raise ValueError(f"Unknown function: {func_name}")

        print("Submitting outputs back to the Assistant...")
        self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=self.thread.id, run_id=self.run.id, tool_outputs=tool_outputs
        )

    def wait_for_completion(self):
        if self.thread and self.run:
            while True:
                time.sleep(5)
                run_status = self.client.beta.threads.runs.retrieve(run_id=self.run.id, thread_id=self.thread.id)
                print(f"RUN STATUS {run_status.model_dump_json(indent=4)}")

                if run_status.status == "completed":
                    self.process_message()
                    break
                elif run_status.status == "requires_action":
                    print('FUNCTION Calling NOW....')
                    self.call_required_functions(
                        required_actions=run_status.required_action.submit_tool_outputs.model_dump())
    
    def run_steps(self):
        run_steps = self.client.beta.threads.runs.steps.list(
            thread_id=self.thread.id, run_id=self.run.id
        )
        print(f"Run-Steps::: {run_steps}")
        return run_steps.data


    # Function for Streamlit
    def get_summary(self):
        return self.summary

def main():
    # news = get_news('bitcoin')
    # print(news[0])
    manager = AssistantManager()

    st.title('News Summarizer')

    with st.form(key="user_input_form"):
        instructions = st.text_input("Enter topic:")
        submit_button = st.form_submit_button(label="Run Assistant")

        if submit_button:
            manager.create_assistant(
                name="News Summarizer",
                instructions="You are a personal article summarizer Assistant who knows how to take a list of article's titles and descriptions and then write a short summary of all the news articles",
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "get_news",
                            "description": "Get the list of articles/news for the given topic",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "topic": {
                                        "type": "string",
                                        "description": "The topic for the news, e.g. bitcoin",
                                    }
                                },
                                "required": ["topic"],
                            },
                        },
                    }
                ],
            )
            manager.create_thread()

            # Add the message and run the assistant
            manager.add_message_to_thread(
                role="user", content=f"summarize the news on this topic {instructions}?"
            )
            manager.run_assistant(instructions="Summarize the news")

            # Wait for completions and process messages
            manager.wait_for_completion()

            summary = manager.get_summary()

            st.write(summary)

            st.text("Run Steps:")
            st.code(manager.run_steps(), line_numbers=True)

if __name__ == "__main__":
    main()