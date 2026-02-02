import requests
r = requests.post('http://127.0.0.1:8002/swarm/scale', json={'count':2}, timeout=5)
print(r.status_code)
print(r.text)
