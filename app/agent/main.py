from xml.parsers.expat import model
import os
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate

sys_msg ="""
You are a World-Class Data Insights Agent. Your goal is to transform complex data into clear, beautiful, and actionable reports that anyone can understand immediately.

IMPORTANT: You MUST write the entire report in {language}.

STRUCTURE YOUR RESPONSE AS FOLLOWS:

1. 🌟 **Executive Summary**: 3-4 bullet points of the most important things found in the data.
2. 📊 **Key Metrics (KPIs)**: Use a table to show the most important numbers (Averages, Totals, Growth).
3. 🔍 **Deep Dive Insights**: 
    - Use sub-headers for different topics (Sales, Time, Geography).
    - Bold important numbers (e.g., **$15,000** or **+25%**).
    - Use emojis to make it friendly.
4. 💡 **Smart Recommendations**: A numbered list of exact actions the user should take based on the data.
5. ❓ **FAQ**: Answer 2-3 obvious questions a business owner might ask about this data.

IMPORTANT RULES:
- Use **Clear & Simple Language** (No technical jargon).
- Use **Tables** and **Lists** as much as possible for readability.
- Use **Horizontal Lines (`---`)** to separate major sections.
- **DO NOT** include any Python/SQL code.
- Provide analysis ONLY based on the provided data.
"""
chat_temp = ChatPromptTemplate.from_messages(
    [
        ("system", sys_msg),
        ("human", "{input}")
    ]
)



from app.config import settings

def load_model(
    model_name: str = "nemotron-3-nano:30b-cloud", 
    reasoning: bool = True, 
    model_type="chat",
    base_url: str = None
) -> ChatOllama:
    
    # Default to settings if base_url is not provided
    # Explicitly fallback to localhost if settings are missing
    ollama_url = base_url or getattr(settings, 'OLLAMA_BASE_URL', "http://127.0.0.1:11434")

    if model_type == "chat":
        model = ChatOllama(
            model=model_name, 
            reasoning=reasoning, 
            base_url=ollama_url,
            num_ctx=4096, # Add some sensible defaults to prevent memory overruns
            temperature=0.7
        )

    elif model_type == "agent":
        model = create_agent(
            llm=ChatOllama(model=model_name, reasoning=reasoning, base_url=ollama_url),
            system_message=SystemMessage(content=sys_msg),
            tools=[]
        )
    
    return model

if __name__ == "__main__":

    import pandas as pd 

    model = load_model()

    df = pd.read_csv(r"https://raw.githubusercontent.com/Abdelrahman142/ai-data-platform/refs/heads/main/cleaned/auto_cleaned_bmw_global_sales_dataset.csv")

    response = model.invoke(chat_temp.invoke({'input': df.to_string()}))

    print(response)
