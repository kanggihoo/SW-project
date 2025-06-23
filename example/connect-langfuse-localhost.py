from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

langfuse = Langfuse(
    public_key="pk-lf-30b7d75b-8cd6-473e-a0c9-fd0a2d7d8196",
    secret_key="sk-lf-9ee371c3-8e6d-4bce-926b-bd9bc3281866",
    host="http://localhost:3000"
)

langfuse_handler = CallbackHandler()

# <Your Langchain code here>
 
# Add handler to run/invoke/call/chat
