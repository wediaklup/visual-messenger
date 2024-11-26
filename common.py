with open(".s3", "r", encoding="utf-8") as f:
    data = f.read()

S3_ACCESS_KEY, S3_SECRET_KEY, S3_ENDPOINT = data.strip().split("\n")
BUCKET = "archiv"
PREFIX = "visual-messenger"

def s3_url_for(endpoint: str) -> str:
    return f"{PREFIX}/{endpoint}"

