from appwrite.client import Client
from appwrite.services.storage import Storage

MONGODB_URI = "mongodb+srv://flutterd26:1Yjf324sdLpdF3CQ@cluster0.dco0p.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DATABASE_NAME = "timebloom"
client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1')
client.set_project('67b05d4a001253d99c6c')
client.set_key('standard_dc33da9ae5cb9efe2f17dac5b7dd22d753014d0d89270a0c95a5cde91b3a68a21dd8bc65db575244e409fc90587baee855bce4d1d610a0a3febdb3880968c08119958ee85f4fbe863961124d6624d8dfa85bbbcf88665adb8c8f45794f75361ec767e26ef73167c3512b8cd4b6cbbaa17e4d8e875d12560353b0503eefcf4cae')
storage = Storage(client)