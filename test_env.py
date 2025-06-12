from dotenv import load_dotenv
import os

load_dotenv()

print("DATABASE_URL:", os.getenv("DATABASE_URL"))
print("ADMIN_API_KEY:", os.getenv("ADMIN_API_KEY"))
print("CORS_ORIGINS:", os.getenv("CORS_ORIGINS"))
print("TRUSTED_HOSTS:", os.getenv("TRUSTED_HOSTS")) 