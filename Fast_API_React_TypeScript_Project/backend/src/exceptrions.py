from fastapi import HTTPException, status

credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )

wrong_trip_place = ValueError("Место отъезда и место прибытия не могут совпадать.")