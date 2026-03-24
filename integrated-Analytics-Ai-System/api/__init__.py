from fastapi import FastAPI

app = FastAPI()



if __name__ == "__main__":
    print(str(app.state))