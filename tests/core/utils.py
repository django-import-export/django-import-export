from _sha256 import sha256


def generate_hashed_content(*, content: str, length: int | None = 20):
    # Hash the content using SHA-256
    hashed_uuid = sha256(content.encode()).hexdigest()

    # Take the first N characters to create a custom length
    custom_length_uuid = hashed_uuid[:length]  # Adjust the length as needed

    return custom_length_uuid
