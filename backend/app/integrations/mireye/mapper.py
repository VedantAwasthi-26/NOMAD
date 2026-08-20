def map_mireye_response(response: dict) -> dict:
    return {
        "lat": response["lat"],
        "lng": response["lng"],
        "fetched_at": response["fetched_at"],
        "fields": response["fields"],
        "partial_failures": response.get("partial_failures", [])
    }