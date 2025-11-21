import requests

url = "https://api.themoviedb.org/3/discover/movie?language=en-US&page=1&sort_by=popularity.desc"

headers = {
    "accept": "application/json",
    "Authorization": "Bearer ******************"
}

response = requests.get(url, headers=headers)

print(response.text)