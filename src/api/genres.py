import requests

url = "https://api.themoviedb.org/3/genre/movie/list?language=en"

headers = {
    "accept": "application/json",
    "Authorization": "Bearer ******************"
}

response = requests.get(url, headers=headers)

print(response.text)