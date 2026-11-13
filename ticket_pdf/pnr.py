"""
Flight Ticket Purchasing System - PNR (Passenger Name Record) Generator
IATA ve veritabanı kısıtlamalarına (^[A-Z0-9]{6}$) tam uyumlu PNR motoru.
"""

import hashlib
import re
import secrets
import string
from typing import Optional, Set

# İnsan gözüyle karıştırılması muhtemel karakterler elenmiş alfabetik-sayısal karakter kümesi:
# 0 (sıfır) ve O harfi, 1 (bir) ve I harfi karıştırılabildiği için çıkarılmıştır.
SAFE_PNR_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
STANDARD_PNR_ALPHABET = string.ascii_uppercase + string.digits


def generate_pnr(
    length: int = 6,
    prefix: Optional[str] = None,
    safe_chars: bool = True,
) -> str:
    """
    Kriptografik olarak güvenli, tam 6 karakterli rastgele PNR kodu üretir.
    """
    alphabet = SAFE_PNR_ALPHABET if safe_chars else STANDARD_PNR_ALPHABET

    if prefix:
        clean_prefix = re.sub(r"[^A-Z0-9]", "", prefix.upper())
        remaining_len = length - len(clean_prefix)
        if remaining_len <= 0:
            raise ValueError(f"Önek uzunluğu ({len(clean_prefix)}) istenen toplam uzunluktan ({length}) küçük olmalıdır.")
        random_part = "".join(secrets.choice(alphabet) for _ in range(remaining_len))
        return f"{clean_prefix}{random_part}"

    return "".join(secrets.choice(alphabet) for _ in range(length))


def validate_pnr(pnr: str) -> bool:
    """
    Madde 20: Veritabanı CHECK (pnr_code ~ '^[A-Z0-9]{6}$') kuralına göre
    tam 6 büyük harf/rakam olup olmadığını denetler.
    """
    if not pnr or not isinstance(pnr, str):
        return False

    cleaned = pnr.strip().upper()
    return bool(re.match(r"^[A-Z0-9]{6}$", cleaned))


def generate_deterministic_pnr(
    flight_number: str,
    seat_number: str,
    passenger_name: str,
    salt: str = "AERO_FLIGHT_SALT",
    length: int = 6,
) -> str:
    """
    Madde 7: [YALNIZCA BİRİM TESTLERİ İÇİN]
    Deterministik PNR üretir; güvenlik gereği gerçek bilet akışında kullanılmamalıdır.
    """
    raw_payload = f"{flight_number}:{seat_number}:{passenger_name}:{salt}".upper()
    hasher = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

    alphabet = SAFE_PNR_ALPHABET
    result = []
    for i in range(0, length * 2, 2):
        chunk = int(hasher[i:i + 2], 16)
        result.append(alphabet[chunk % len(alphabet)])

    return "".join(result)


def generate_unique_pnrs(count: int, length: int = 6, prefix: Optional[str] = None) -> Set[str]:
    """
    Belirtilen adette benzersiz PNR kümesi üretir.
    """
    pnrs: Set[str] = set()
    max_attempts = count * 20
    attempts = 0

    while len(pnrs) < count and attempts < max_attempts:
        pnrs.add(generate_pnr(length=length, prefix=prefix))
        attempts += 1

    if len(pnrs) < count:
        raise RuntimeError(f"{count} adet benzersiz PNR üretilemedi.")

    return pnrs
