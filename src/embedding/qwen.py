import time

import requests

url = 'https://api.siliconflow.com/v1/rerank'

payload = {
    'model': 'Qwen/Qwen3-Reranker-8B',
    'query': 'Apple',
    'documents': ['apple', 'banana', 'fruit', 'vegetable'],
    'top_n': 4,
    'return_documents': True,
    'max_chunks_per_doc': 123,
    'overlap_tokens': 79,
}
headers = {'Authorization': 'Bearer sk-wbfylrfzypivpewvsvcwmceqbagekirkrnsevhabfvijejkc', 'Content-Type': 'application/json'}
start_time = time.perf_counter()
response = requests.post(url, json=payload, headers=headers)
end_time = time.perf_counter()
print(f'Time taken: {end_time - start_time} seconds')
print(response.json())
