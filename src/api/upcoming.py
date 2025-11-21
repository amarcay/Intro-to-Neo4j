import requests

url = "https://api.themoviedb.org/3/movie/upcoming?language=FR&page=1"

headers = {
    "accept": "application/json",
    "Authorization": "Bearer ******************"
}

response = requests.get(url, headers=headers)

print(response.text)