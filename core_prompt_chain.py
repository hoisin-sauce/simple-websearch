import lmstudio as lms
SERVER_API_HOST = "localhost:1234"

with lms.Client(SERVER_API_HOST) as client:
    model = client.llm.model("deepseek/deepseek-r1-0528-qwen3-8b")

    for fragment in model.respond_stream("What is the meaning of life?"):
        print(fragment.content, end="", flush=True)
    print() # Advance to a new line at the end of the response
