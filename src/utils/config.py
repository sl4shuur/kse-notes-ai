import os
import dotenv
try:
    from .config_helper import find_project_root
except ImportError:
    from config_helper import find_project_root


# Base of the project
BASE_DIR = find_project_root()
DATA_DIR = BASE_DIR / "data"

# Direcitories for testing and outputs
TEST_DATA_DIR = BASE_DIR / "test_data"
TEST_OUTPUT_DIR = BASE_DIR / "test_output"
CONTENT_DIR = BASE_DIR / "content"

# Temporary directory for audio chunks
TEMP_AUDIO_DIR = BASE_DIR / "temp_audio_chunks"

# .env file loading
dotenv_path = BASE_DIR / ".env"
if not dotenv_path.exists():
    print(f".env file not found at {dotenv_path}")
    raise FileNotFoundError(f"Environment file not found: {dotenv_path}")

dotenv.load_dotenv(dotenv_path)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("GROQ_API_KEY not found in environment variables.")
    raise ValueError(
        "GROQ_API_KEY not found in environment variables. Please set it in the .env file."
    )

for directory in [DATA_DIR, TEST_DATA_DIR, TEST_OUTPUT_DIR, CONTENT_DIR, TEMP_AUDIO_DIR]:
    if directory.exists() and directory.is_file():
        directory.unlink()  # Remove the file if a file exists with the same name
    directory.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    print(f"Base directory: {BASE_DIR}")
