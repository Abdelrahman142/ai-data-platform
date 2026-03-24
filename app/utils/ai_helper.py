import pandas as pd
import json
import httpx

from app.agent.main import load_model, chat_temp
from langchain_core.prompts import PromptTemplate

rename_prompt = PromptTemplate.from_template("""
You are a data engineering assistant. You are given a sample of a dataset with cryptic or generic column names (like 'unnamed_0', 'col1', etc.).
Your task is to analyze the data values and suggest meaningful, descriptive English column names.

DATA SAMPLES:
{sample_data}

CURRENT COLUMNS:
{columns}

INSTRUCTIONS:
1. Look at the values in each column to understand what they represent (e.g., prices, dates, names, IDs, statuses).
2. Suggest a single, clear, snake_case English name for each column.
3. Return ONLY a valid JSON object where the keys are the current column names and the values are your suggested names.
4. Do not include any explanation or other text.

Example Output:
{{ "unnamed_0": "transaction_id", "col_1": "order_date", "unnamed_5": "unit_price" }}
""")

forecast_prompt = PromptTemplate.from_template("""
You are a senior data scientist and forecasting expert. 
Your task is to analyze the provided dataset summary and generate a detailed predictive forecast or trend analysis.

DATASET SUMMARY:
{dataset_str}

USER SPECIFIC REQUEST (if any):
{user_prompt}

INSTRUCTIONS:
1. Identify any time-series elements (dates, years, months) or trends in the data.
2. Provide a 3-step predictive forecast (Short, Medium, and Long term) based on current data patterns.
3. Quantify potential growth or decline if possible.
4. Highlight major risks or external factors that could influence this forecast.
5. Format your response in professional Markdown. Use charts/tables if appropriate (text-based).
6. Response MUST be in {language}.

Wait! If the user's data isn't time-based, focus on 'Trend Analysis' and 'Future Probability' instead.
""")

async def analyze_and_rename_columns(df: pd.DataFrame, model_name: str = "nemotron-3-nano:30b-cloud") -> pd.DataFrame:
    """
    Uses AI to identify what cryptic columns represent and renames them appropriately.
    """
    try:
        # 1. Translate content first to help the model understand Arabic values
        df_translated = translate_content(df.head(10))
        
        # 2. Prepare the prompt
        sample_str = df_translated.to_string()
        columns_str = ", ".join(df.columns)
        
        model = load_model(model_name=model_name, reasoning=False)
        
        # 3. Get AI suggestions
        response = await model.ainvoke(rename_prompt.format(sample_data=sample_str, columns=columns_str))
        
        # Extract JSON from response
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Basic JSON extraction in case it includes triple backticks
        import json
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        rename_map = json.loads(content)
        
        # 4. Apply renaming to the original dataframe
        return df.rename(columns=rename_map)
    except Exception as e:
        print(f"Column rename failed: {str(e)}")
        return df

import re
from deep_translator import GoogleTranslator

def is_arabic(text):
    """Checks if a string contains Arabic characters."""
    if not isinstance(text, str):
        return False
    return bool(re.search(r'[\u0600-\u06FF]', text))

def translate_content(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detects Arabic text in column names and string content and translates them to English.
    """
    translated_df = df.copy()
    translator = GoogleTranslator(source='auto', target='en')
    
    # 1. Translate Arabic Column Names
    new_columns = {}
    for col in translated_df.columns:
        if is_arabic(str(col)):
            try:
                new_columns[col] = translator.translate(str(col))
            except:
                new_columns[col] = col
        else:
            new_columns[col] = col
    translated_df.rename(columns=new_columns, inplace=True)
    
    # 2. Translate Arabic Cell Values
    string_cols = translated_df.select_dtypes(include=['object']).columns
    
    for col in string_cols:
        # Check if column likely contains Arabic
        sample_values = translated_df[col].dropna().head(10).astype(str).tolist()
        if any(is_arabic(val) for val in sample_values):
            # To handle "alot of data", we only translate unique values to be efficient
            unique_vals = translated_df[col].dropna().unique()
            
            # Optimization: If too many unique values (e.g. unique descriptions), 
            # we only translate the most frequent ones to avoid performance bottleneck
            if len(unique_vals) > 50:
                top_vals = translated_df[col].value_counts().index[:50]
                unique_vals_to_translate = top_vals
            else:
                unique_vals_to_translate = unique_vals
                
            translation_map = {}
            for val in unique_vals_to_translate:
                val_str = str(val)
                if is_arabic(val_str):
                    try:
                        translation_map[val] = translator.translate(val_str)
                    except:
                        translation_map[val] = val
                else:
                    translation_map[val] = val
            
            # Map the translated values back to the dataframe
            translated_df[col] = translated_df[col].map(lambda x: translation_map.get(x, x))
            
    return translated_df

def format_dataset_for_ai(df: pd.DataFrame) -> str:
    """
    Creates a smart summary of the dataset to provide maximum insight 
    while staying within the AI's context window limits.
    """
    # 1. Translate Arabic to English first
    try:
        df = translate_content(df)
    except:
        pass

    # 2. Build a structured summary
    summary = []
    summary.append(f"DATASET OVERVIEW:")
    summary.append(f"- Total Rows: {len(df)}")
    summary.append(f"- Total Columns: {len(df.columns)}")
    summary.append(f"- Columns: {', '.join(df.columns)}")
    
    summary.append("\nDESCRIPTIVE STATISTICS (Numeric):")
    summary.append(df.describe().to_string())
    
    summary.append("\nDATA TYPES & MISSING VALUES:")
    info_df = pd.DataFrame({
        'Type': df.dtypes.astype(str),
        'Missing': df.isnull().sum(),
        'Unique': df.nunique()
    })
    summary.append(info_df.to_string())

    # 3. Add a sample of the data (Smart Sampling)
    # If the dataset is small, include more. If large, include representative chunks.
    summary.append("\nDATA SAMPLES (Top 10 and Random 5):")
    if len(df) <= 15:
        summary.append(df.to_string())
    else:
        top_5 = df.head(10)
        random_5 = df.sample(5) if len(df) > 10 else pd.DataFrame()
        summary.append("Top 10 rows:")
        summary.append(top_5.to_string())
        summary.append("\nRandom sample of 5 rows:")
        summary.append(random_5.to_string())

    return "\n".join(summary)

async def call_external_ai_api(dataset_str: str, user_prompt: str, model_name: str = "nemotron-3-nano:30b-cloud", reasoning: bool = True, language: str = "English") -> str:
    """
    Performs a call to the integrated AI model using LangChain and Ollama.
    """
    try:
        model = load_model(model_name=model_name, reasoning=reasoning, model_type="chat")
        
        # Using ainvoke for async support in FastAPI
        # Pass the language to the system message via the template variables
        response = await model.ainvoke(
            chat_temp.invoke({
                "language": language,
                "input": user_prompt + "\n\n" + dataset_str
            })
        )
        
        # Check if response has 'content' or is a string
        if hasattr(response, 'content'):
            return response.content
        return str(response)

    except Exception as e:
        return f"AI Error: {str(e)}"

async def run_predictive_forecast(dataset_str: str, user_prompt: str, model_name: str = "nemotron-3-nano:30b-cloud", reasoning: bool = True, language: str = "English") -> str:
    """
    Specifically generates a predictive forecast report based on the dataset.
    """
    try:
        model = load_model(model_name=model_name, reasoning=reasoning, model_type="chat")
        
        response = await model.ainvoke(
            forecast_prompt.format(
                dataset_str=dataset_str,
                user_prompt=user_prompt,
                language=language
            )
        )
        
        if hasattr(response, 'content'):
            return response.content
        return str(response)

    except Exception as e:
        return f"Forecasting Error: {str(e)}"
