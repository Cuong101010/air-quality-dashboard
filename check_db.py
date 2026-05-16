
import database
import os

# Set DATABASE_URL if needed, but it's hardcoded in database.py as a fallback
count = database.get_row_count()
print(f"Total rows in sensor_data: {count}")

latest = database.get_latest()
print(f"Latest record: {latest}")
