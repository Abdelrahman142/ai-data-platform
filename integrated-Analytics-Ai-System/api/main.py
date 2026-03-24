from . import FastAPI, app
from agent.main import load_model, chat_temp


@app.get('/gen')
def genreport (
    model_name: str = "nemotron-3-nano:30b-cloud",
    reasoning: bool = True,
    model_type: str = "chat",
    dataset: str = "",
    prompt: str = ""
):
    model = load_model(model_name=model_name, reasoning=reasoning, model_type=model_type)

    response = model.invoke(
    chat_temp.invoke({"input":prompt + "\n\n" + dataset})
    )
    
    return{'response': response}
